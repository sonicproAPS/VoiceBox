"""HTTP API for text-to-speech and speech-to-text.

Run with:  uvicorn voicebox.main:app --reload   (from the backend/ directory)
"""

import logging
import shutil
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import Settings, get_settings
from .stt import STTEngine
from .stt.whisper_engine import ModelUnavailable, UnknownModel, WhisperEngine
from .tts import TTSEngine
from .tts.piper_engine import InvalidVoiceId, PiperEngine, VoiceNotFound

logger = logging.getLogger(__name__)


class TTSRequest(BaseModel):
    text: str = Field(min_length=1)
    voice: str
    speed: float = Field(default=1.0, ge=0.5, le=2.0)


def create_app(
    settings: Optional[Settings] = None,
    tts: Optional[TTSEngine] = None,
    stt: Optional[STTEngine] = None,
) -> FastAPI:
    settings = settings or get_settings()
    tts = tts or PiperEngine(settings.voices_dir, use_cuda=settings.device == "cuda")
    stt = stt or WhisperEngine(
        settings.whisper_dir, default_model=settings.whisper_model, device=settings.device
    )

    app = FastAPI(title="VoiceBox", version="0.1.0")

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    # --- Text to speech -------------------------------------------------

    @app.get("/api/tts/voices")
    def list_voices():
        return [asdict(v) for v in tts.list_voices()]

    @app.post("/api/tts/voices/{voice_id}/download")
    def download_voice(voice_id: str):
        try:
            return asdict(tts.download_voice(voice_id))
        except InvalidVoiceId as e:
            raise HTTPException(400, str(e))
        except OSError as e:  # network errors (urllib.error.URLError) included
            logger.exception("Voice download failed")
            raise HTTPException(502, f"Download failed: {e}")

    @app.post("/api/tts")
    def synthesize(req: TTSRequest):
        text = req.text.strip()
        if not text:
            raise HTTPException(400, "Text is empty")
        if len(text) > settings.max_tts_chars:
            raise HTTPException(400, f"Text exceeds {settings.max_tts_chars} characters")
        try:
            audio = tts.synthesize(text, req.voice, speed=req.speed)
        except InvalidVoiceId as e:
            raise HTTPException(400, str(e))
        except VoiceNotFound as e:
            raise HTTPException(404, str(e))
        return Response(audio, media_type="audio/wav")

    # --- Speech to text -------------------------------------------------

    @app.get("/api/stt/models")
    def list_models():
        return {"models": stt.list_models(), "default": settings.whisper_model}

    @app.post("/api/stt")
    def transcribe(
        file: UploadFile = File(...),
        language: Optional[str] = Form(None),
        model: Optional[str] = Form(None),
        translate: bool = Form(False),
    ):
        suffix = Path(file.filename or "").suffix[:10]
        with tempfile.NamedTemporaryFile(suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp.flush()
            try:
                result = stt.transcribe(
                    Path(tmp.name), language=language or None, model=model or None,
                    translate=translate,
                )
            except UnknownModel as e:
                raise HTTPException(400, str(e))
            except ModelUnavailable as e:
                logger.exception("Whisper model unavailable")
                raise HTTPException(502, str(e))
            except Exception as e:
                # PyAV raises a variety of errors for unreadable/corrupt audio.
                if type(e).__module__.startswith("av"):
                    raise HTTPException(400, f"Could not decode audio: {e}")
                raise
        return asdict(result)

    # --- Frontend -------------------------------------------------------

    dist = settings.frontend_dist
    if (dist / "index.html").exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str):
            if path.startswith("api/"):
                raise HTTPException(404, "Not found")
            file = (dist / path).resolve()
            if path and file.is_file() and file.is_relative_to(dist.resolve()):
                return FileResponse(file)
            return FileResponse(dist / "index.html")

    return app


app = create_app()
