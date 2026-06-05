"""API tests for /api/managers — M6-T1."""

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
        {
            "sub": "viewer1",
            "role": "viewer",
            "exp": datetime.now(tz=UTC) + timedelta(hours=1),
        },
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


class TestManagersAuth:
    async def test_no_token_returns_401_on_list(self, test_app) -> None:  # type: ignore[no-untyped-def]
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/managers")
        assert resp.status_code == 401

    async def test_no_token_returns_401_on_create(self, test_app) -> None:  # type: ignore[no-untyped-def]
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/managers", json={})
        assert resp.status_code == 401

    async def test_viewer_cannot_create_manager(self, test_app) -> None:  # type: ignore[no-untyped-def]
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/managers",
                headers=_viewer_headers(),
                json={"full_name": "Test", "position": "Dev"},
            )
        assert resp.status_code == 403

    async def test_viewer_can_list_managers(self, test_app) -> None:  # type: ignore[no-untyped-def]
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/managers", headers=_viewer_headers())
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_viewer_cannot_update_manager(self, test_app) -> None:  # type: ignore[no-untyped-def]
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.patch(
                f"/api/managers/{uuid.uuid4()}",
                headers=_viewer_headers(),
                json={"full_name": "New"},
            )
        assert resp.status_code == 403

    async def test_viewer_cannot_delete_manager(self, test_app) -> None:  # type: ignore[no-untyped-def]
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.delete(
                f"/api/managers/{uuid.uuid4()}",
                headers=_viewer_headers(),
            )
        assert resp.status_code == 403


class TestManagersCRUD:
    async def test_admin_create_manager_returns_201(self, test_app) -> None:  # type: ignore[no-untyped-def]
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/managers",
                headers=admin_headers(),
                json={"full_name": "Иван Иванов", "position": "Менеджер"},
            )
        assert resp.status_code == 201
        body = resp.json()
        assert body["full_name"] == "Иван Иванов"
        assert body["position"] == "Менеджер"
        assert "id" in body
        assert body["is_active"] is True

    async def test_create_manager_with_device_id(self, test_app) -> None:  # type: ignore[no-untyped-def]
        device_id = f"dev-{uuid.uuid4().hex[:8]}"
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/managers",
                headers=admin_headers(),
                json={"full_name": "Пётр", "position": "Dev", "device_id": device_id},
            )
        assert resp.status_code == 201
        assert resp.json()["device_id"] == device_id

    async def test_duplicate_device_id_returns_409(self, test_app) -> None:  # type: ignore[no-untyped-def]
        device_id = f"dup-{uuid.uuid4().hex[:8]}"
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            await client.post(
                "/api/managers",
                headers=admin_headers(),
                json={"full_name": "First", "position": "Dev", "device_id": device_id},
            )
            resp = await client.post(
                "/api/managers",
                headers=admin_headers(),
                json={"full_name": "Second", "position": "Dev", "device_id": device_id},
            )
        assert resp.status_code == 409

    async def test_list_managers_includes_created(self, test_app) -> None:  # type: ignore[no-untyped-def]
        name = f"ListTest-{uuid.uuid4().hex[:6]}"
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            await client.post(
                "/api/managers",
                headers=admin_headers(),
                json={"full_name": name, "position": "Dev"},
            )
            resp = await client.get("/api/managers", headers=admin_headers())
        assert resp.status_code == 200
        names = [m["full_name"] for m in resp.json()]
        assert name in names

    async def test_get_manager_by_id(self, test_app) -> None:  # type: ignore[no-untyped-def]
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            create_resp = await client.post(
                "/api/managers",
                headers=admin_headers(),
                json={"full_name": "GetById", "position": "Dev"},
            )
            manager_id = create_resp.json()["id"]
            resp = await client.get(f"/api/managers/{manager_id}", headers=admin_headers())
        assert resp.status_code == 200
        assert resp.json()["id"] == manager_id

    async def test_get_nonexistent_manager_returns_404(self, test_app) -> None:  # type: ignore[no-untyped-def]
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.get(
                f"/api/managers/{uuid.uuid4()}", headers=admin_headers()
            )
        assert resp.status_code == 404

    async def test_admin_update_manager_full_name(self, test_app) -> None:  # type: ignore[no-untyped-def]
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            create_resp = await client.post(
                "/api/managers",
                headers=admin_headers(),
                json={"full_name": "Original", "position": "Dev"},
            )
            manager_id = create_resp.json()["id"]
            resp = await client.patch(
                f"/api/managers/{manager_id}",
                headers=admin_headers(),
                json={"full_name": "Updated"},
            )
        assert resp.status_code == 200
        assert resp.json()["full_name"] == "Updated"

    async def test_deactivate_manager_soft_deletes(self, test_app) -> None:  # type: ignore[no-untyped-def]
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            create_resp = await client.post(
                "/api/managers",
                headers=admin_headers(),
                json={"full_name": "ToDeactivate", "position": "Dev"},
            )
            manager_id = create_resp.json()["id"]
            resp = await client.delete(
                f"/api/managers/{manager_id}", headers=admin_headers()
            )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    async def test_deactivated_manager_still_listed(self, test_app) -> None:  # type: ignore[no-untyped-def]
        """Soft delete preserves record (history not destroyed)."""
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            create_resp = await client.post(
                "/api/managers",
                headers=admin_headers(),
                json={"full_name": "SoftDeleted", "position": "Dev"},
            )
            manager_id = create_resp.json()["id"]
            await client.delete(f"/api/managers/{manager_id}", headers=admin_headers())
            resp = await client.get(f"/api/managers/{manager_id}", headers=admin_headers())
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False
