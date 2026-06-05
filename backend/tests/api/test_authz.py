"""Authorization tests — JWT guards + role enforcement — M5-T3."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt as jose_jwt

pytestmark = pytest.mark.anyio

_JWT_SECRET = "testsecret"
_JWT_ALG = "HS256"


def _make_token(sub: str, role: str, expired: bool = False) -> str:
    delta = timedelta(hours=-1) if expired else timedelta(hours=1)
    return jose_jwt.encode(
        {"sub": sub, "role": role, "exp": datetime.now(tz=UTC) + delta},
        _JWT_SECRET,
        algorithm=_JWT_ALG,
    )


@pytest.fixture
def test_app():  # type: ignore[no-untyped-def]
    from app.config.settings import Settings
    from app.main import create_app

    settings = Settings(
        DATABASE_URL="postgresql+asyncpg://badge:badge@localhost:5434/badge",
        MINIO_ENDPOINT="http://localhost:9000",
        MINIO_BUCKET="test-recordings",
        ADMIN_LOGIN="admin",
        ADMIN_PASSWORD="adminpass123",
        JWT_SECRET=_JWT_SECRET,
        JWT_EXPIRE_MINUTES=60,
    )
    return create_app(settings=settings)


class TestNoToken:
    async def test_recordings_without_token_returns_401(self, test_app) -> None:  # type: ignore[no-untyped-def]
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/recordings")
        assert resp.status_code == 401

    async def test_uploads_without_token_returns_401(self, test_app) -> None:  # type: ignore[no-untyped-def]
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/uploads")
        assert resp.status_code == 401

    async def test_health_is_public(self, test_app) -> None:  # type: ignore[no-untyped-def]
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.get("/health")
        assert resp.status_code == 200


class TestExpiredToken:
    async def test_expired_token_returns_401(self, test_app) -> None:  # type: ignore[no-untyped-def]
        token = _make_token("admin", "admin", expired=True)
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/recordings", headers={"Authorization": f"Bearer {token}"}
            )
        assert resp.status_code == 401


class TestViewerRole:
    async def test_viewer_can_list_recordings(self, test_app) -> None:  # type: ignore[no-untyped-def]
        token = _make_token("user1", "viewer")
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/recordings", headers={"Authorization": f"Bearer {token}"}
            )
        assert resp.status_code == 200

    async def test_viewer_cannot_patch_analysis(self, test_app) -> None:  # type: ignore[no-untyped-def]
        import uuid

        token = _make_token("user1", "viewer")
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.patch(
                f"/api/recordings/{uuid.uuid4()}/analysis",
                headers={"Authorization": f"Bearer {token}"},
                json={"score": 90.0},
            )
        assert resp.status_code == 403

    async def test_viewer_cannot_upload(self, test_app) -> None:  # type: ignore[no-untyped-def]
        token = _make_token("user1", "viewer")
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/uploads",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 403


class TestAdminRole:
    async def test_admin_can_list_recordings(self, test_app) -> None:  # type: ignore[no-untyped-def]
        token = _make_token("admin", "admin")
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/recordings", headers={"Authorization": f"Bearer {token}"}
            )
        assert resp.status_code == 200

    async def test_admin_can_patch_analysis(self, test_app) -> None:  # type: ignore[no-untyped-def]
        import uuid

        token = _make_token("admin", "admin")
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.patch(
                f"/api/recordings/{uuid.uuid4()}/analysis",
                headers={"Authorization": f"Bearer {token}"},
                json={"score": 90.0},
            )
        # 404 (no such recording) is fine — proves it got past auth
        assert resp.status_code in (200, 404)
