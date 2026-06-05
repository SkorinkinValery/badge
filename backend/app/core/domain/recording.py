"""Recording domain entity."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import field_validator
from pydantic.dataclasses import dataclass

from app.core.domain.enums import RecordingStatus


@dataclass(frozen=True)
class Recording:
    id: uuid.UUID
    manager_id: uuid.UUID
    channel: str
    consent_flag: bool
    status: RecordingStatus
    created_at: datetime
    retention_until: datetime | None
    audio_path: str | None
    stage_error: str | None

    @field_validator("channel")
    @classmethod
    def channel_not_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("channel must not be empty")
        return v
