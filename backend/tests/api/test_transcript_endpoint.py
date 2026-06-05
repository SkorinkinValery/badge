"""API tests for GET /api/recordings/{id}/transcript — M3-T6.

Requires Postgres (integration mark).
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


def _make_wav() -> bytes:
    num_samples = 800
    data_size = num_samples * 2
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + data_size, b"WAVE",
        b"fmt ", 16, 1, 1, 16000, 32000, 2, 16,
        b"data", data_size,
    )
    return header + b"\x00" * data_size


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


@pytest.fixture(scope="module")
def test_app(sync_engine):  # type: ignore[no-untyped-def]
    from sqlalchemy.pool import NullPool

    from app.config.settings import Settings
    from app.db.session import make_session_factory
    from app.main import create_app

    settings = Settings(
        DATABASE_URL=DB_URL,
        MINIO_ENDPOINT=MINIO_ENDPOINT,
        MINIO_BUCKET="test-recordings",
    )
    app = create_app(settings=settings)
    app.state.session_factory = make_session_factory(
        DB_URL, pool_pre_ping=False, poolclass=NullPool
    )
    return app


@pytest.fixture(scope="module")
def manager_id(sync_engine) -> uuid.UUID:  # type: ignore[no-untyped-def]
    from sqlalchemy.orm import Session

    from app.db.repositories.manager_repo import ManagerRepository

    with Session(sync_engine) as sess:
        mgr = ManagerRepository(sess).create(
            full_name="Transcript Test Manager",
            position="Менеджер",
            device_id=None,
            is_active=True,
            default_script_id=None,
        )
        sess.commit()
        return mgr.id  # type: ignore[return-value]


@pytest.fixture(scope="module")
async def recording_with_transcript(test_app, sync_engine, manager_id: uuid.UUID) -> uuid.UUID:
    """Create a recording and manually insert a transcript into the DB."""
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/uploads",
            data={"manager_id": str(manager_id), "consent_flag": "true"},
            files={"file": ("test.wav", io.BytesIO(_make_wav()), "audio/wav")},
        )
    recording_id = uuid.UUID(resp.json()["recording_id"])

    from sqlalchemy.orm import Session

    from app.db.models.transcript import TranscriptModel

    with Session(sync_engine) as sess:
        t = TranscriptModel(
            id=uuid.uuid4(),
            recording_id=recording_id,
            full_text="Добрый день, слушаю вас.",
            segments=[
                {"start": 0.0, "end": 2.0, "text": "Добрый день,"},
                {"start": 2.0, "end": 4.0, "text": "слушаю вас."},
            ],
            detected_language="ru",
        )
        sess.add(t)
        sess.commit()

    return recording_id


@pytest.fixture(scope="module")
async def recording_without_transcript(test_app, manager_id: uuid.UUID) -> uuid.UUID:
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/uploads",
            data={"manager_id": str(manager_id), "consent_flag": "true"},
            files={"file": ("no_transcript.wav", io.BytesIO(_make_wav()), "audio/wav")},
        )
    return uuid.UUID(resp.json()["recording_id"])


class TestTranscriptEndpoint:
    @pytest.mark.anyio
    async def test_transcript_returns_200_with_full_text(
        self, test_app, recording_with_transcript: uuid.UUID
    ) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.get(f"/api/recordings/{recording_with_transcript}/transcript")
        assert resp.status_code == 200
        body = resp.json()
        assert "full_text" in body
        assert "Добрый день" in body["full_text"]

    @pytest.mark.anyio
    async def test_transcript_returns_segments_with_timecodes(
        self, test_app, recording_with_transcript: uuid.UUID
    ) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.get(f"/api/recordings/{recording_with_transcript}/transcript")
        body = resp.json()
        assert "segments" in body
        assert len(body["segments"]) > 0
        seg = body["segments"][0]
        assert "start" in seg and "end" in seg and "text" in seg

    @pytest.mark.anyio
    async def test_transcript_returns_detected_language(
        self, test_app, recording_with_transcript: uuid.UUID
    ) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.get(f"/api/recordings/{recording_with_transcript}/transcript")
        body = resp.json()
        assert body["detected_language"] == "ru"

    @pytest.mark.anyio
    async def test_missing_transcript_returns_404(
        self, test_app, recording_without_transcript: uuid.UUID
    ) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.get(f"/api/recordings/{recording_without_transcript}/transcript")
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_nonexistent_recording_returns_404(self, test_app) -> None:
        fake_id = uuid.uuid4()
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.get(f"/api/recordings/{fake_id}/transcript")
        assert resp.status_code == 404
