"""Tests for GET /api/kpi — KPI rubric config for the UI."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from tests.api.conftest import _JWT_SECRET, admin_headers


def _make_app():  # type: ignore[no-untyped-def]
    from app.config.settings import Settings
    from app.main import create_app

    return create_app(settings=Settings(JWT_SECRET=_JWT_SECRET))


@pytest.mark.anyio
async def test_kpi_requires_auth() -> None:
    app = _make_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/kpi")
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_kpi_returns_rubric() -> None:
    app = _make_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/kpi", headers=admin_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0
    item = data[0]
    assert {"id", "label", "type", "weight", "applies_to", "include_in_score"} <= set(item)


@pytest.mark.anyio
async def test_kpi_includes_known_ids_and_labels() -> None:
    app = _make_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/kpi", headers=admin_headers())
    data = resp.json()
    by_id = {k["id"]: k for k in data}
    # Labels must be human-readable (non-empty, different from the raw id).
    assert "greeting" in by_id
    assert by_id["greeting"]["label"]
    assert by_id["greeting"]["label"] != "greeting"
    # script_compliance is a script-only KPI and must be advertised as such.
    assert by_id["script_compliance"]["applies_to"] == "script"
