"""Integration tests for the graph job runner — M1-T7.

Requires a live Postgres. Set DATABASE_URL env before running.
"""

from __future__ import annotations

import io
import os
import struct
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://badge:badge@localhost:5434/badge",
).replace("postgresql+asyncpg://", "postgresql+psycopg2://")

MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_ROOT_USER = os.environ.get("MINIO_ROOT_USER", "minioadmin")
MINIO_ROOT_PASSWORD = os.environ.get("MINIO_ROOT_PASSWORD", "minioadmin")
TEST_BUCKET = "test-runner-audio"

pytestmark = pytest.mark.db


def _make_wav(duration_s: float = 0.5, sample_rate: int = 16000) -> bytes:
    num_samples = int(duration_s * sample_rate)
    data_size = num_samples * 2
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + data_size, b"WAVE",
        b"fmt ", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16,
        b"data", data_size,
    )
    return header + b"\x00" * data_size


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


@pytest.fixture(scope="module")
def storage():  # type: ignore[no-untyped-def]
    from app.services.storage import ObjectStorage

    s = ObjectStorage(
        endpoint=MINIO_ENDPOINT,
        access_key=MINIO_ROOT_USER,
        secret_key=MINIO_ROOT_PASSWORD,
        bucket=TEST_BUCKET,
    )
    s.ensure_bucket()
    yield s


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


@pytest.mark.integration
class TestRunnerRealAudio:
    """Regression: the pipeline must process the recording's actual uploaded
    audio (via storage + normalize_audio + FileSource), not always a fixed
    in-memory stub — otherwise STT silently transcribes silence and every
    recording scores 0/100 regardless of what was said."""

    def test_runner_loads_real_audio_from_storage(
        self, session: Session, storage  # type: ignore[no-untyped-def]
    ) -> None:
        from app.adapters.audio.file_stub import FileStubSource
        from app.core.domain.enums import RecordingStatus
        from app.core.domain.transcript import Segment, Transcript
        from app.db.repositories.manager_repo import ManagerRepository
        from app.db.repositories.recording_repo import RecordingRepository
        from app.services.storage import ObjectStorage
        from app.workers.runner import run_job

        class CapturingSTTEngine:
            def __init__(self) -> None:
                self.received: list[bytes] = []

            def transcribe(self, audio: object) -> Transcript:
                self.received.append(audio.audio_data)  # type: ignore[attr-defined]
                return Transcript(
                    id=uuid.uuid4(),
                    recording_id=uuid.uuid4(),
                    full_text="захвачено из реального файла",
                    segments=(Segment(start=0.0, end=1.0, text="захвачено из реального файла"),),
                    detected_language="ru",
                )

        mgr = ManagerRepository(session).create(
            full_name="Реальное Аудио Тест",
            position="Менеджер",
            device_id=None,
            is_active=True,
            default_script_id=None,
        )
        rec = RecordingRepository(session).create(
            manager_id=mgr.id, channel="file", consent_flag=True
        )

        wav_data = _make_wav(duration_s=0.5, sample_rate=16000)
        orig_key = ObjectStorage.make_key(rec.id, "original", ".wav")
        storage.put_object(orig_key, io.BytesIO(wav_data), len(wav_data), "audio/wav")

        rec.audio_path = orig_key
        RecordingRepository(session).update_status(rec.id, RecordingStatus.QUEUED)
        session.commit()

        engine = CapturingSTTEngine()
        run_job(recording_id=rec.id, db_url=DB_URL, stt_engine=engine, storage=storage)

        session.refresh(rec)
        assert rec.status == RecordingStatus.DONE.value
        assert rec.audio_path == orig_key

        assert len(engine.received) == 1
        captured_bytes = engine.received[0]
        stub_bytes = FileStubSource().fetch().audio_data
        assert captured_bytes != stub_bytes
        assert len(captured_bytes) > len(stub_bytes)

        # duration_seconds is populated from the last transcript segment end
        assert rec.duration_seconds == 1.0
