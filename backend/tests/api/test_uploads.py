"""Integration tests for POST /api/uploads — M2-T5.

Requires MinIO and Postgres.
"""

from __future__ import annotations

import io
import os
import struct
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.integration

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://badge:badge@localhost:5434/badge",
)
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "http://localhost:9000")


def _make_wav(sample_rate: int = 16000, duration_s: float = 0.3) -> bytes:
    num_samples = int(sample_rate * duration_s)
    data_size = num_samples * 2
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + data_size, b"WAVE",
        b"fmt ", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16,
        b"data", data_size,
    )
    return header + b"\x00" * data_size


def _make_mp3() -> bytes:
    return b"\xff\xfb\x90\x00" + b"\x00" * 200


@pytest.fixture(scope="module")
def test_app():  # type: ignore[no-untyped-def]
    from sqlalchemy.pool import NullPool

    from app.config.settings import Settings
    from app.db.session import make_session_factory
    from app.main import create_app

    settings = Settings(
        DATABASE_URL=DB_URL,
        MINIO_ENDPOINT=MINIO_ENDPOINT,
        MINIO_BUCKET="test-uploads",
    )
    app = create_app(settings=settings)
    # Use NullPool in tests to avoid event-loop-closed teardown errors
    app.state.session_factory = make_session_factory(
        DB_URL, pool_pre_ping=False, poolclass=NullPool
    )
    return app


@pytest.fixture(scope="module")
def sync_engine():  # type: ignore[no-untyped-def]
    from sqlalchemy import create_engine

    import app.db.models  # noqa: F401
    from app.db.base import Base

    sync_url = DB_URL.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    engine = create_engine(sync_url, echo=False)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(sync_engine):  # type: ignore[no-untyped-def]
    from sqlalchemy.orm import Session

    with Session(sync_engine) as sess:
        yield sess
        sess.rollback()


@pytest.fixture(scope="module")
def manager_id(sync_engine) -> uuid.UUID:  # type: ignore[no-untyped-def]
    from sqlalchemy.orm import Session

    from app.db.repositories.manager_repo import ManagerRepository

    with Session(sync_engine) as sess:
        mgr = ManagerRepository(sess).create(
            full_name="Upload Test Manager",
            position="Менеджер",
            device_id=None,
            is_active=True,
            default_script_id=None,
        )
        sess.commit()
        return mgr.id  # type: ignore[return-value]


class TestUploadEndpoint:
    @pytest.mark.anyio
    async def test_valid_wav_returns_201(self, test_app, manager_id: uuid.UUID) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/uploads",
                data={"manager_id": str(manager_id), "consent_flag": "true"},
                files={"file": ("recording.wav", io.BytesIO(_make_wav()), "audio/wav")},
            )
        assert resp.status_code == 201
        body = resp.json()
        assert "recording_id" in body
        assert uuid.UUID(body["recording_id"])

    @pytest.mark.anyio
    async def test_recording_has_queued_status(
        self, test_app, manager_id: uuid.UUID, db_session
    ) -> None:
        from app.core.domain.enums import RecordingStatus
        from app.db.repositories.recording_repo import RecordingRepository

        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/uploads",
                data={"manager_id": str(manager_id), "consent_flag": "true"},
                files={"file": ("rec.wav", io.BytesIO(_make_wav()), "audio/wav")},
            )
        recording_id = uuid.UUID(resp.json()["recording_id"])
        db_session.expire_all()
        rec = RecordingRepository(db_session).get(recording_id)
        assert rec is not None
        assert rec.status == RecordingStatus.QUEUED.value

    @pytest.mark.anyio
    async def test_invalid_format_returns_422(self, test_app, manager_id: uuid.UUID) -> None:
        ogg = b"OggS" + b"\x00" * 100
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/uploads",
                data={"manager_id": str(manager_id), "consent_flag": "true"},
                files={"file": ("recording.ogg", io.BytesIO(ogg), "audio/ogg")},
            )
        assert resp.status_code == 422

    @pytest.mark.anyio
    async def test_missing_consent_returns_422(self, test_app, manager_id: uuid.UUID) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/uploads",
                data={"manager_id": str(manager_id), "consent_flag": "false"},
                files={"file": ("recording.wav", io.BytesIO(_make_wav()), "audio/wav")},
            )
        assert resp.status_code == 422

    @pytest.mark.anyio
    async def test_audio_stored_in_minio(
        self, test_app, manager_id: uuid.UUID, db_session
    ) -> None:
        from app.db.repositories.recording_repo import RecordingRepository

        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/uploads",
                data={"manager_id": str(manager_id), "consent_flag": "true"},
                files={"file": ("rec.wav", io.BytesIO(_make_wav()), "audio/wav")},
            )
        recording_id = uuid.UUID(resp.json()["recording_id"])
        db_session.expire_all()
        rec = RecordingRepository(db_session).get(recording_id)
        assert rec is not None
        assert rec.audio_path is not None
        assert "recordings/" in rec.audio_path
