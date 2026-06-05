"""FileSource: AudioSource adapter backed by MinIO storage."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.core.ports.audio_source import AudioPayload
from app.services.storage import ObjectStorage


class FileSource:
    """Reads a normalized audio file from MinIO and returns it as AudioPayload."""

    def __init__(
        self,
        storage: ObjectStorage,
        normalized_key: str,
        manager_id: uuid.UUID,
        consent_flag: bool,
        channel: str = "file",
        started_at: datetime | None = None,
    ) -> None:
        self._storage = storage
        self._key = normalized_key
        self._manager_id = manager_id
        self._consent_flag = consent_flag
        self._channel = channel
        self._started_at = started_at or datetime.now(tz=UTC)

    def fetch(self) -> AudioPayload:
        data = self._storage.get_object(self._key).read()
        return AudioPayload(
            audio_data=data,
            sample_rate=16000,
            manager_id=self._manager_id,
            channel=self._channel,
            started_at=self._started_at,
            consent_flag=self._consent_flag,
        )
