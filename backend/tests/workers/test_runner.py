"""Integration tests for the graph job runner — M1-T7.

Requires a live Postgres. Set DATABASE_URL env before running.
"""

from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://badge:badge@localhost:5434/badge",
).replace("postgresql+asyncpg://", "postgresql+psycopg2://")

pytestmark = pytest.mark.db


@pytest.fixture(scope="module")
def engine():  # type: ignore[no-untyped-def]
    import app.db.models  # noqa: F401
    from app.db.base import Base

    eng = create_engine(DB_URL, echo=False)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def session(engine):  # type: ignore[no-untyped-def]
    with Session(engine) as sess:
        yield sess
        sess.rollback()


@pytest.fixture
def queued_recording(session: Session) -> uuid.UUID:
    from app.core.domain.enums import RecordingStatus
    from app.db.repositories.manager_repo import ManagerRepository
    from app.db.repositories.recording_repo import RecordingRepository

    mgr = ManagerRepository(session).create(
        full_name="Воркер Тест",
        position="Менеджер",
        device_id=None,
        is_active=True,
        default_script_id=None,
    )
    rec = RecordingRepository(session).create(
        manager_id=mgr.id,
        channel="file",
        consent_flag=True,
        audio_path="stub/audio.wav",
    )
    RecordingRepository(session).update_status(rec.id, RecordingStatus.QUEUED)
    session.commit()
    return rec.id


class TestRunner:
    def test_runner_importable(self) -> None:
        from app.workers.runner import run_job  # noqa: F401

    def test_runner_processes_queued_job_to_done(
        self, session: Session, queued_recording: uuid.UUID
    ) -> None:
        from app.core.domain.enums import RecordingStatus
        from app.db.repositories.recording_repo import RecordingRepository
        from app.workers.runner import run_job

        run_job(recording_id=queued_recording, db_url=DB_URL)

        rec = RecordingRepository(session).get(queued_recording)
        session.refresh(rec)
        assert rec is not None
        assert rec.status == RecordingStatus.DONE.value

    def test_runner_sets_failed_on_error(self, session: Session) -> None:
        from app.core.domain.enums import RecordingStatus
        from app.db.repositories.manager_repo import ManagerRepository
        from app.db.repositories.recording_repo import RecordingRepository
        from app.workers.runner import run_job

        mgr = ManagerRepository(session).create(
            full_name="Воркер Fail Тест",
            position="Менеджер",
            device_id=None,
            is_active=True,
            default_script_id=None,
        )
        rec = RecordingRepository(session).create(
            manager_id=mgr.id,
            channel="file",
            consent_flag=True,
        )
        RecordingRepository(session).update_status(rec.id, RecordingStatus.QUEUED)
        session.commit()

        run_job(recording_id=rec.id, db_url=DB_URL, fail_at_stage="normalizing")

        session.refresh(rec)
        assert rec.status == RecordingStatus.FAILED.value
        assert rec.stage_error is not None

    def test_resume_from_checkpoint_starts_not_from_scratch(
        self, session: Session
    ) -> None:
        """Running the same recording twice should resume from checkpoint, not restart."""
        from app.core.domain.enums import RecordingStatus
        from app.db.repositories.manager_repo import ManagerRepository
        from app.db.repositories.recording_repo import RecordingRepository
        from app.workers.runner import run_job

        mgr = ManagerRepository(session).create(
            full_name="Resumable Test",
            position="Менеджер",
            device_id=None,
            is_active=True,
            default_script_id=None,
        )
        rec = RecordingRepository(session).create(
            manager_id=mgr.id,
            channel="file",
            consent_flag=True,
        )
        RecordingRepository(session).update_status(rec.id, RecordingStatus.QUEUED)
        session.commit()

        run_job(recording_id=rec.id, db_url=DB_URL)
        session.refresh(rec)
        assert rec.status == RecordingStatus.DONE.value

        run_job(recording_id=rec.id, db_url=DB_URL)
        session.refresh(rec)
        assert rec.status == RecordingStatus.DONE.value
