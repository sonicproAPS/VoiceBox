"""Speech-to-text with faster-whisper (Whisper on CTranslate2).

Models are downloaded from Hugging Face on first use into
``<data_dir>/whisper``. Any audio format supported by FFmpeg/PyAV is accepted,
including the WebM/Opus produced by browser microphone recordings.
"""

import threading
from pathlib import Path
from typing import Optional

from .base import Segment, Transcription

MODELS = [
    "tiny",
    "base",
    "small",
    "medium",
    "large-v3",
    "large-v3-turbo",
]


class UnknownModel(ValueError):
    pass


class ModelUnavailable(RuntimeError):
    """The model could not be downloaded or loaded."""


class WhisperEngine:
    def __init__(self, models_dir: Path, default_model: str = "small", device: str = "auto"):
        self.models_dir = models_dir
        self.default_model = default_model
        self.device = device
        self._loaded: dict = {}
        self._lock = threading.Lock()

    def list_models(self) -> list[str]:
        return list(MODELS)

    def _load(self, name: str):
        if name not in MODELS:
            raise UnknownModel(f"Unknown Whisper model '{name}'")
        with self._lock:
            model = self._loaded.get(name)
            if model is None:
                from faster_whisper import WhisperModel

                self.models_dir.mkdir(parents=True, exist_ok=True)
                try:
                    model = WhisperModel(
                        name,
                        device=self.device,
                        compute_type="default",
                        download_root=str(self.models_dir),
                    )
                except Exception as e:
                    raise ModelUnavailable(f"Could not load Whisper model '{name}': {e}") from e
                self._loaded[name] = model
            return model

    def transcribe(
        self,
        audio_path: Path,
        language: Optional[str] = None,
        model: Optional[str] = None,
        translate: bool = False,
    ) -> Transcription:
        whisper = self._load(model or self.default_model)
        segments, info = whisper.transcribe(
            str(audio_path),
            language=language or None,
            task="translate" if translate else "transcribe",
            vad_filter=True,
        )
        # `segments` is a lazy generator: transcription happens while iterating.
        result = [Segment(start=s.start, end=s.end, text=s.text.strip()) for s in segments]
        return Transcription(
            text=" ".join(s.text for s in result if s.text),
            language=info.language,
            language_probability=info.language_probability,
            duration=info.duration,
            segments=result,
        )
