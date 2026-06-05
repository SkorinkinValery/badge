"""MicSource: AudioSource adapter backed by WebSocket chunk buffer (M7-T3).

Accepts assembled audio data from ChunkBuffer and satisfies the AudioSource
contract identically to FileSource — the pipeline graph is agnostic to source.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.core.ports.audio_source import AudioPayload

TARGET_SAMPLE_RATE = 16000


class MicSource:
    """AudioSource implementation for microphone input via WebSocket buffer.

    Constructed after `stop` is received and the buffer is flushed into
    a single normalized audio payload.
    """

    def __init__(
        self,
        audio_data: bytes,
        manager_id: uuid.UUID,
        consent_flag: bool,
        started_at: datetime | None = None,
        sample_rate: int = TARGET_SAMPLE_RATE,
    ) -> None:
        self._audio_data = audio_data
        self._manager_id = manager_id
        self._consent_flag = consent_flag
        self._started_at = started_at or datetime.now(tz=UTC)
        self._sample_rate = sample_rate

    def fetch(self) -> AudioPayload:
        return AudioPayload(
            audio_data=self._audio_data,
            sample_rate=self._sample_rate,
            manager_id=self._manager_id,
            channel="mic",
            started_at=self._started_at,
            consent_flag=self._consent_flag,
        )
