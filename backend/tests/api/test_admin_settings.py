"""API tests for GET/PUT /api/admin/settings — M8-T6."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from tests.api.conftest import _JWT_SECRET, admin_headers

pytestmark = pytest.mark.anyio


def _make_app() -> object:
    from app.config.settings import Settings
    from app.main import create_app

    settings = Settings(
        DATABASE_URL="postgresql+asyncpg://badge:badge@localhost:5434/badge",
        JWT_SECRET=_JWT_SECRET,
    )
    app = create_app(settings=settings)
    return app


@pytest.fixture
def app() -> object:
    return _make_app()


@pytest.fixture
async def client(app: object):  # type: ignore[no-untyped-def]

    async with AsyncClient(
        transport=ASGITransport(app=app),  # type: ignore[arg-type]
        base_url="http://test",
    ) as c:
        yield c


class TestGetCrmSettings:
    async def test_get_returns_200(self, client: AsyncClient) -> None:
        resp = await client.get(
            "/api/admin/settings", headers=admin_headers()
        )
        assert resp.status_code == 200

    async def test_get_contains_active_crm(self, client: AsyncClient) -> None:
        resp = await client.get("/api/admin/settings", headers=admin_headers())
        body = resp.json()
        assert "active_crm" in body

    async def test_get_contains_available_providers(self, client: AsyncClient) -> None:
        resp = await client.get("/api/admin/settings", headers=admin_headers())
        body = resp.json()
        providers = body.get("available_providers", [])
        assert "json" in providers
        assert "google_sheets" in providers
        assert "webhook" in providers
        assert "bitrix24" in providers

    async def test_get_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.get("/api/admin/settings")
        assert resp.status_code == 401


class TestPutCrmSettings:
    async def test_put_changes_active_crm(self, client: AsyncClient) -> None:
        resp = await client.put(
            "/api/admin/settings",
            json={"active_crm": "json", "params": {}},
            headers=admin_headers(),
        )
        assert resp.status_code == 200
        assert resp.json()["active_crm"] == "json"

    async def test_put_persists_within_session(self, client: AsyncClient) -> None:
        await client.put(
            "/api/admin/settings",
            json={"active_crm": "webhook", "params": {"url": "https://example.com"}},
            headers=admin_headers(),
        )
        resp = await client.get("/api/admin/settings", headers=admin_headers())
        assert resp.json()["active_crm"] == "webhook"

    async def test_put_unknown_provider_returns_422(self, client: AsyncClient) -> None:
        resp = await client.put(
            "/api/admin/settings",
            json={"active_crm": "nonexistent_crm"},
            headers=admin_headers(),
        )
        assert resp.status_code == 422

    async def test_put_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.put(
            "/api/admin/settings",
            json={"active_crm": "json"},
        )
        assert resp.status_code == 401
