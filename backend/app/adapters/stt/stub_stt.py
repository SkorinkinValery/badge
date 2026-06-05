"""StubSTTEngine — deterministic STT adapter for testing without real ASR."""

from __future__ import annotations

import uuid

from app.core.domain.transcript import Segment, Transcript
from app.core.ports.audio_source import AudioPayload


class StubSTTEngine:
    """Returns a fixed Transcript regardless of input. Satisfies STTEngine protocol."""

    def transcribe(self, audio: AudioPayload) -> Transcript:
        return Transcript(
            id=uuid.uuid4(),
            recording_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
            full_text="Добрый день, чем могу помочь? Хорошо, понял вас.",
            segments=(
                Segment(start=0.0, end=2.5, text="Добрый день, чем могу помочь?"),
                Segment(start=2.5, end=5.0, text="Хорошо, понял вас."),
            ),
            detected_language="ru",
        )
