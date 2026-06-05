"""FileStubSource — deterministic stub for testing without real audio files."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.core.ports.audio_source import AudioPayload


class FileStubSource:
    """Returns a fixed PCM-like payload; satisfies AudioSource protocol."""

    def fetch(self) -> AudioPayload:
        return AudioPayload(
            audio_data=b"\x00\x01" * 800,  # 1600 bytes of silence-like data
            sample_rate=16000,
            manager_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            channel="file",
            started_at=datetime.now(tz=UTC),
            consent_flag=True,
        )
