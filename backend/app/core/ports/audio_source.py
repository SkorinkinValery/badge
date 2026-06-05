"""AudioSource port and AudioPayload DTO."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict


class AudioPayload(BaseModel):
    model_config = ConfigDict(frozen=True)

    audio_data: bytes
    sample_rate: int
    manager_id: uuid.UUID
    channel: str
    started_at: datetime
    consent_flag: bool


@runtime_checkable
class AudioSource(Protocol):
    """Normalised audio source for any input channel."""

    def fetch(self) -> AudioPayload:
        """Fetch normalised audio with metadata."""
        ...
