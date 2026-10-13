"""Common interface for speech-to-text engines."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Protocol


@dataclass(frozen=True)
class Segment:
    start: float
    end: float
    text: str


@dataclass(frozen=True)
class Transcription:
    text: str
    language: str
    language_probability: float
    duration: float
    segments: list[Segment] = field(default_factory=list)


class STTEngine(Protocol):
    def list_models(self) -> list[str]: ...

    def transcribe(
        self,
        audio_path: Path,
        language: Optional[str] = None,
        model: Optional[str] = None,
        translate: bool = False,
    ) -> Transcription: ...
