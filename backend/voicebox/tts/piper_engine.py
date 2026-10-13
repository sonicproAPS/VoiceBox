"""Text-to-speech with Piper (https://github.com/OHF-Voice/piper1-gpl).

Voices are small ONNX models (20-100 MB) that run in real time on a CPU.
They are downloaded on demand from Hugging Face into ``<data_dir>/voices``.
"""

import io
import re
import tempfile
import threading
import wave
from pathlib import Path

from .base import VoiceInfo

# Voices offered in the UI even before they are downloaded. Any other Piper
# voice (see https://huggingface.co/rhasspy/piper-voices) can be installed by
# id through the API, or by dropping its .onnx + .onnx.json in the voices dir.
CATALOG = [
    "it_IT-paola-medium",
    "it_IT-riccardo-x_low",
    "en_US-lessac-medium",
    "en_US-amy-medium",
    "en_GB-alba-medium",
    "es_ES-davefx-medium",
    "fr_FR-siwis-medium",
    "de_DE-thorsten-medium",
    "pt_BR-faber-medium",
]

VOICE_ID = re.compile(r"^(?P<lang>[a-z]{2,3}_[A-Z]{2})-(?P<name>[A-Za-z0-9_]+)-(?P<quality>[a-z_]+)$")


class VoiceNotFound(Exception):
    pass


class InvalidVoiceId(ValueError):
    pass


def parse_voice_id(voice_id: str) -> re.Match:
    match = VOICE_ID.match(voice_id)
    if not match:
        raise InvalidVoiceId(
            f"Invalid voice id '{voice_id}', expected <lang>_<REGION>-<name>-<quality>"
        )
    return match


class PiperEngine:
    def __init__(self, voices_dir: Path, use_cuda: bool = False):
        self.voices_dir = voices_dir
        self.use_cuda = use_cuda
        self._loaded: dict = {}
        self._lock = threading.Lock()

    def _model_path(self, voice_id: str) -> Path:
        return self.voices_dir / f"{voice_id}.onnx"

    def _is_installed(self, voice_id: str) -> bool:
        model = self._model_path(voice_id)
        return model.exists() and model.with_suffix(".onnx.json").exists()

    def _info(self, voice_id: str) -> VoiceInfo:
        match = parse_voice_id(voice_id)
        return VoiceInfo(
            id=voice_id,
            name=match["name"].replace("_", " ").title(),
            language=match["lang"],
            quality=match["quality"],
            installed=self._is_installed(voice_id),
        )

    def list_voices(self) -> list[VoiceInfo]:
        ids = set(CATALOG)
        if self.voices_dir.exists():
            for model in self.voices_dir.glob("*.onnx"):
                if VOICE_ID.match(model.stem):
                    ids.add(model.stem)
        return sorted((self._info(v) for v in ids), key=lambda v: (v.language, v.id))

    def download_voice(self, voice_id: str) -> VoiceInfo:
        parse_voice_id(voice_id)
        from piper.download_voices import download_voice

        self.voices_dir.mkdir(parents=True, exist_ok=True)
        # Download into a temp dir first so an interrupted download never
        # leaves a truncated model that looks installed.
        with tempfile.TemporaryDirectory(dir=self.voices_dir) as tmp:
            download_voice(voice_id, Path(tmp))
            for suffix in (".onnx.json", ".onnx"):
                (Path(tmp) / f"{voice_id}{suffix}").replace(self.voices_dir / f"{voice_id}{suffix}")
        return self._info(voice_id)

    def _load(self, voice_id: str):
        parse_voice_id(voice_id)
        with self._lock:
            voice = self._loaded.get(voice_id)
            if voice is None:
                if not self._is_installed(voice_id):
                    raise VoiceNotFound(f"Voice '{voice_id}' is not installed")
                from piper import PiperVoice

                voice = PiperVoice.load(self._model_path(voice_id), use_cuda=self.use_cuda)
                self._loaded[voice_id] = voice
            return voice

    def synthesize(self, text: str, voice_id: str, speed: float = 1.0) -> bytes:
        from piper import SynthesisConfig

        voice = self._load(voice_id)
        config = SynthesisConfig(length_scale=1.0 / speed)
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            voice.synthesize_wav(text, wav_file, syn_config=config)
        return buffer.getvalue()
