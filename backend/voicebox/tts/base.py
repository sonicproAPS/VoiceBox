"""Common interface for text-to-speech engines."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class VoiceInfo:
    id: str
    name: str
    language: str
    quality: str
    installed: bool


class TTSEngine(Protocol):
    def list_voices(self) -> list[VoiceInfo]: ...

    def download_voice(self, voice_id: str) -> VoiceInfo: ...

    def synthesize(self, text: str, voice_id: str, speed: float = 1.0) -> bytes:
        """Return a complete WAV file."""
        ...
