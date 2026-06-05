"""STTEngine port."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.core.domain import Transcript
from app.core.ports.audio_source import AudioPayload


@runtime_checkable
class STTEngine(Protocol):
    """Speech-to-text engine: converts audio to Transcript."""

    def transcribe(self, audio: AudioPayload) -> Transcript:
        """Transcribe audio payload into a Transcript with segments."""
        ...
