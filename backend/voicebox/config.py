"""Runtime settings, read from environment variables."""

import os
from dataclasses import dataclass, field
from pathlib import Path


def _env_path(name: str, default: Path) -> Path:
    value = os.environ.get(name)
    return Path(value).expanduser() if value else default


@dataclass(frozen=True)
class Settings:
    data_dir: Path = field(
        default_factory=lambda: _env_path(
            "VOICEBOX_DATA_DIR", Path(__file__).resolve().parents[2] / "data"
        )
    )
    # Whisper model used when the request does not specify one.
    whisper_model: str = field(
        default_factory=lambda: os.environ.get("VOICEBOX_WHISPER_MODEL", "small")
    )
    # "cpu", "cuda" or "auto".
    device: str = field(default_factory=lambda: os.environ.get("VOICEBOX_DEVICE", "auto"))
    max_tts_chars: int = field(
        default_factory=lambda: int(os.environ.get("VOICEBOX_MAX_TTS_CHARS", "5000"))
    )
    frontend_dist: Path = field(
        default_factory=lambda: _env_path(
            "VOICEBOX_FRONTEND_DIST",
            Path(__file__).resolve().parents[2] / "frontend" / "dist",
        )
    )

    @property
    def voices_dir(self) -> Path:
        return self.data_dir / "voices"

    @property
    def whisper_dir(self) -> Path:
        return self.data_dir / "whisper"


def get_settings() -> Settings:
    return Settings()
