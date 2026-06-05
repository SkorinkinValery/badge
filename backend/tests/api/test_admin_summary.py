"""API tests for /api/admin/summary — M6-T4."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from tests.api.conftest import _JWT_SECRET, admin_headers

pytestmark = pytest.mark.anyio

_DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://badge:badge@localhost:5434/badge",
)


def _viewer_headers(secret: str = _JWT_SECRET) -> dict[str, str]:
    from jose import jwt as jose_jwt

    token = jose_jwt.encode(
        {"sub": "viewer1", "role": "viewer", "exp": datetime.now(tz=UTC) + timedelta(hours=1)},
        secret,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def sync_engine():  # type: ignore[no-untyped-def]
    from sqlalchemy import create_engine

    import app.db.models  # noqa: F401
    from app.db.base import Base

    sync_url = _DB_URL.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
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
        DATABASE_URL=_DB_URL,
        MINIO_ENDPOINT="http://localhost:9000",
        MINIO_BUCKET="test-recordings",
        JWT_SECRET=_JWT_SECRET,
    )
    app = create_app(settings=settings)
    app.state.session_factory = make_session_factory(
        _DB_URL, pool_pre_ping=False, poolclass=NullPool
    )
    return app


class TestAdminSummaryAuth:
    async def test_no_token_returns_401(self, test_app) -> None:  # type: ignore[no-untyped-def]
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/admin/summary",
                params={"manager_id": str(uuid.uuid4()), "date": "2026-06-01"},
            )
        assert resp.status_code == 401

    async def test_viewer_can_access_summary(self, test_app) -> None:  # type: ignore[no-untyped-def]
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/admin/summary",
                headers=_viewer_headers(),
                params={"manager_id": str(uuid.uuid4()), "date": "2026-06-01"},
            )
        assert resp.status_code == 200


class TestAdminSummaryData:
    async def test_empty_day_returns_zeros(self, test_app) -> None:  # type: ignore[no-untyped-def]
        nonexistent_manager = uuid.uuid4()
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/admin/summary",
                headers=admin_headers(),
                params={"manager_id": str(nonexistent_manager), "date": "2000-01-01"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_recordings"] == 0
        assert body["avg_score"] is None
        assert body["violations"] == []

    async def test_summary_has_required_fields(self, test_app) -> None:  # type: ignore[no-untyped-def]
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/admin/summary",
                headers=admin_headers(),
                params={"manager_id": str(uuid.uuid4()), "date": "2026-06-01"},
            )
        body = resp.json()
        required = {
            "manager_id",
            "date",
            "total_recordings",
            "total_duration_s",
            "avg_duration_s",
            "avg_score",
            "kpi_stats",
            "violations",
            "top_issues",
        }
        assert required.issubset(body.keys())

    async def test_invalid_date_returns_422(self, test_app) -> None:  # type: ignore[no-untyped-def]
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/admin/summary",
                headers=admin_headers(),
                params={"manager_id": str(uuid.uuid4()), "date": "not-a-date"},
            )
        assert resp.status_code == 422
