"""Integration tests for GET /api/recordings — M2-T6.

Requires Postgres.
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
            full_name="Recordings Test Manager",
            position="Менеджер",
            device_id=None,
            is_active=True,
            default_script_id=None,
        )
        sess.commit()
        return mgr.id  # type: ignore[return-value]


@pytest.fixture(scope="module")
async def seeded_recording_id(test_app, manager_id: uuid.UUID) -> uuid.UUID:
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/uploads",
            data={"manager_id": str(manager_id), "consent_flag": "true"},
            files={"file": ("seed.wav", io.BytesIO(_make_wav()), "audio/wav")},
        )
    return uuid.UUID(resp.json()["recording_id"])


class TestRecordingsEndpoint:
    @pytest.mark.anyio
    async def test_list_returns_200(self, test_app) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/recordings")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.anyio
    async def test_list_contains_status(
        self, test_app, seeded_recording_id: uuid.UUID
    ) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/recordings")
        items = resp.json()
        ids = [item["id"] for item in items]
        assert str(seeded_recording_id) in ids

    @pytest.mark.anyio
    async def test_detail_returns_recording(
        self, test_app, seeded_recording_id: uuid.UUID
    ) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.get(f"/api/recordings/{seeded_recording_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == str(seeded_recording_id)
        assert body["status"] in {
            "uploaded", "queued", "normalizing", "transcribing",
            "analyzing", "scoring", "exporting", "done", "failed",
        }

    @pytest.mark.anyio
    async def test_filter_by_manager_id(
        self, test_app, manager_id: uuid.UUID, seeded_recording_id: uuid.UUID
    ) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.get(f"/api/recordings?manager_id={manager_id}")
        assert resp.status_code == 200
        items = resp.json()
        assert all(item["manager_id"] == str(manager_id) for item in items)

    @pytest.mark.anyio
    async def test_missing_recording_returns_404(self, test_app) -> None:
        missing_id = uuid.uuid4()
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.get(f"/api/recordings/{missing_id}")
        assert resp.status_code == 404
