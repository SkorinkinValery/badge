"""Recording repository."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.domain.enums import RecordingStatus
from app.db.models.recording import RecordingModel


class RecordingRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        manager_id: uuid.UUID,
        channel: str,
        consent_flag: bool,
        audio_path: str | None = None,
    ) -> RecordingModel:
        r = RecordingModel(
            id=uuid.uuid4(),
            manager_id=manager_id,
            channel=channel,
            consent_flag=consent_flag,
            audio_path=audio_path,
            status=RecordingStatus.UPLOADED.value,
            created_at=datetime.now(tz=UTC),
        )
        self._session.add(r)
        self._session.flush()
        return r

    def get(self, recording_id: uuid.UUID) -> RecordingModel | None:
        return self._session.get(RecordingModel, recording_id)

    def update_status(
        self,
        recording_id: uuid.UUID,
        status: RecordingStatus,
        stage_error: str | None = None,
    ) -> None:
        r = self._session.get(RecordingModel, recording_id)
        if r is None:
            raise ValueError(f"Recording {recording_id} not found")
        r.status = status.value
        if stage_error is not None:
            r.stage_error = stage_error
        self._session.flush()
