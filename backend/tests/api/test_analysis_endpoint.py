"""API tests for GET/PATCH /api/recordings/{id}/analysis — M4-T8.

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
            full_name="Analysis Test Manager",
            position="Менеджер",
            device_id=None,
            is_active=True,
            default_script_id=None,
        )
        sess.commit()
        return mgr.id  # type: ignore[return-value]


@pytest.fixture(scope="module")
async def recording_with_analysis(test_app, sync_engine, manager_id: uuid.UUID) -> uuid.UUID:
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/uploads",
            data={"manager_id": str(manager_id), "consent_flag": "true"},
            files={"file": ("analysis_test.wav", io.BytesIO(_make_wav()), "audio/wav")},
        )
    recording_id = uuid.UUID(resp.json()["recording_id"])

    from sqlalchemy.orm import Session

    from app.db.models.analysis import AnalysisModel

    with Session(sync_engine) as sess:
        a = AnalysisModel(
            id=uuid.uuid4(),
            recording_id=recording_id,
            summary="Менеджер хорошо представился и выявил потребность.",
            kpi_json={
                "greeting": {"value": 8.0, "quote": "Добрый день", "comment": "хорошо"},
                "needs_discovery": {"value": 7.0, "quote": "расскажите о проблеме", "comment": "ок"},
            },
            score=75.0,
            verdict="~",
            mode="baseline",
            weights_version="v10.0",
        )
        sess.add(a)
        sess.commit()

    return recording_id


@pytest.fixture(scope="module")
async def recording_no_analysis(test_app, manager_id: uuid.UUID) -> uuid.UUID:
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/uploads",
            data={"manager_id": str(manager_id), "consent_flag": "true"},
            files={"file": ("no_analysis.wav", io.BytesIO(_make_wav()), "audio/wav")},
        )
    return uuid.UUID(resp.json()["recording_id"])


class TestAnalysisGetEndpoint:
    @pytest.mark.anyio
    async def test_get_analysis_returns_200(
        self, test_app, recording_with_analysis: uuid.UUID
    ) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.get(f"/api/recordings/{recording_with_analysis}/analysis")
        assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_get_analysis_has_summary(
        self, test_app, recording_with_analysis: uuid.UUID
    ) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.get(f"/api/recordings/{recording_with_analysis}/analysis")
        body = resp.json()
        assert "summary" in body
        assert "менеджер" in body["summary"].lower()

    @pytest.mark.anyio
    async def test_get_analysis_has_kpi_json(
        self, test_app, recording_with_analysis: uuid.UUID
    ) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.get(f"/api/recordings/{recording_with_analysis}/analysis")
        body = resp.json()
        assert "kpi_json" in body
        assert "greeting" in body["kpi_json"]

    @pytest.mark.anyio
    async def test_get_analysis_has_score_and_verdict(
        self, test_app, recording_with_analysis: uuid.UUID
    ) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.get(f"/api/recordings/{recording_with_analysis}/analysis")
        body = resp.json()
        assert body["score"] == 75.0
        assert body["verdict"] == "~"

    @pytest.mark.anyio
    async def test_get_analysis_has_mode(
        self, test_app, recording_with_analysis: uuid.UUID
    ) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.get(f"/api/recordings/{recording_with_analysis}/analysis")
        body = resp.json()
        assert body["mode"] == "baseline"

    @pytest.mark.anyio
    async def test_get_analysis_missing_returns_404(
        self, test_app, recording_no_analysis: uuid.UUID
    ) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.get(f"/api/recordings/{recording_no_analysis}/analysis")
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_get_analysis_nonexistent_recording_404(self, test_app) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.get(f"/api/recordings/{uuid.uuid4()}/analysis")
        assert resp.status_code == 404


class TestAnalysisPatchEndpoint:
    @pytest.mark.anyio
    async def test_patch_score_accepted(
        self, test_app, recording_with_analysis: uuid.UUID
    ) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.patch(
                f"/api/recordings/{recording_with_analysis}/analysis",
                json={"score": 90.0, "verdict": "+", "corrected_by": "supervisor"},
            )
        assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_patch_preserves_auto_score(
        self, test_app, recording_with_analysis: uuid.UUID
    ) -> None:
        """After PATCH, auto_score (original) is still accessible."""
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.get(f"/api/recordings/{recording_with_analysis}/analysis")
        body = resp.json()
        assert "auto_score" in body

    @pytest.mark.anyio
    async def test_patch_missing_analysis_404(
        self, test_app, recording_no_analysis: uuid.UUID
    ) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.patch(
                f"/api/recordings/{recording_no_analysis}/analysis",
                json={"score": 90.0},
            )
        assert resp.status_code == 404
