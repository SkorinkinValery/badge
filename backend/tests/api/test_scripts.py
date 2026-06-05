"""API tests for /api/scripts — M6-T2."""

from __future__ import annotations

import io
import os
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from tests.api.conftest import _JWT_SECRET, admin_headers

pytestmark = pytest.mark.anyio

_DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://badge:badge@localhost:5434/badge",
)

_TXT_CONTENT = b"1. Introduce yourself\n2. Identify needs\n3. Make offer\n4. Close"
_MD_CONTENT = b"# Sales Script\n## Step 1: Greeting\nIntroduce yourself warmly."


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


class TestScriptsAuth:
    async def test_no_token_returns_401(self, test_app) -> None:  # type: ignore[no-untyped-def]
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/scripts")
        assert resp.status_code == 401

    async def test_viewer_cannot_create_script(self, test_app) -> None:  # type: ignore[no-untyped-def]
        from datetime import UTC, datetime, timedelta

        from jose import jwt as jose_jwt

        token = jose_jwt.encode(
            {"sub": "v", "role": "viewer", "exp": datetime.now(tz=UTC) + timedelta(hours=1)},
            _JWT_SECRET,
            algorithm="HS256",
        )
        headers = {"Authorization": f"Bearer {token}"}
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/scripts",
                headers=headers,
                data={"name": "test"},
                files={"file": ("s.txt", io.BytesIO(_TXT_CONTENT), "text/plain")},
            )
        assert resp.status_code == 403


class TestScriptsCRUD:
    async def test_create_script_txt_returns_201(self, test_app) -> None:  # type: ignore[no-untyped-def]
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/scripts",
                headers=admin_headers(),
                data={"name": "Script TXT"},
                files={"file": ("script.txt", io.BytesIO(_TXT_CONTENT), "text/plain")},
            )
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "Script TXT"
        assert "id" in body
        assert body["active_version_id"] is not None

    async def test_create_script_md_returns_201(self, test_app) -> None:  # type: ignore[no-untyped-def]
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/scripts",
                headers=admin_headers(),
                data={"name": "Script MD"},
                files={"file": ("script.md", io.BytesIO(_MD_CONTENT), "text/markdown")},
            )
        assert resp.status_code == 201
        assert resp.json()["active_version_id"] is not None

    async def test_invalid_format_returns_422(self, test_app) -> None:  # type: ignore[no-untyped-def]
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/scripts",
                headers=admin_headers(),
                data={"name": "Bad Script"},
                files={"file": ("script.docx", io.BytesIO(b"PK\x03\x04"), "application/octet-stream")},
            )
        assert resp.status_code == 422

    async def test_upload_new_version_creates_version_2(self, test_app) -> None:  # type: ignore[no-untyped-def]
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            create_resp = await client.post(
                "/api/scripts",
                headers=admin_headers(),
                data={"name": "Versioned Script"},
                files={"file": ("v1.txt", io.BytesIO(_TXT_CONTENT), "text/plain")},
            )
            script_id = create_resp.json()["id"]
            ver_resp = await client.post(
                f"/api/scripts/{script_id}/versions",
                headers=admin_headers(),
                files={"file": ("v2.txt", io.BytesIO(b"Updated content"), "text/plain")},
            )
        assert ver_resp.status_code == 201
        assert ver_resp.json()["version"] == 2

    async def test_versions_are_immutable(self, test_app) -> None:  # type: ignore[no-untyped-def]
        """Old versions preserved after new upload."""
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            create_resp = await client.post(
                "/api/scripts",
                headers=admin_headers(),
                data={"name": "Immutable Script"},
                files={"file": ("s.txt", io.BytesIO(b"Version one"), "text/plain")},
            )
            script_id = create_resp.json()["id"]
            await client.post(
                f"/api/scripts/{script_id}/versions",
                headers=admin_headers(),
                files={"file": ("s.txt", io.BytesIO(b"Version two"), "text/plain")},
            )
            vers_resp = await client.get(
                f"/api/scripts/{script_id}/versions",
                headers=admin_headers(),
            )
        versions = vers_resp.json()
        assert len(versions) == 2
        contents = {v["content"] for v in versions}
        assert "Version one" in contents
        assert "Version two" in contents

    async def test_list_scripts(self, test_app) -> None:  # type: ignore[no-untyped-def]
        name = f"ListScript-{uuid.uuid4().hex[:6]}"
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            await client.post(
                "/api/scripts",
                headers=admin_headers(),
                data={"name": name},
                files={"file": ("s.txt", io.BytesIO(_TXT_CONTENT), "text/plain")},
            )
            resp = await client.get("/api/scripts", headers=admin_headers())
        assert resp.status_code == 200
        names = [s["name"] for s in resp.json()]
        assert name in names

    async def test_get_script_by_id(self, test_app) -> None:  # type: ignore[no-untyped-def]
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            create_resp = await client.post(
                "/api/scripts",
                headers=admin_headers(),
                data={"name": "Get By ID"},
                files={"file": ("s.txt", io.BytesIO(_TXT_CONTENT), "text/plain")},
            )
            script_id = create_resp.json()["id"]
            resp = await client.get(f"/api/scripts/{script_id}", headers=admin_headers())
        assert resp.status_code == 200
        assert resp.json()["id"] == script_id

    async def test_set_active_version(self, test_app) -> None:  # type: ignore[no-untyped-def]
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            create_resp = await client.post(
                "/api/scripts",
                headers=admin_headers(),
                data={"name": "Active Ver Script"},
                files={"file": ("s.txt", io.BytesIO(b"Version 1"), "text/plain")},
            )
            script_id = create_resp.json()["id"]
            v1_id = create_resp.json()["active_version_id"]

            v2_resp = await client.post(
                f"/api/scripts/{script_id}/versions",
                headers=admin_headers(),
                files={"file": ("s.txt", io.BytesIO(b"Version 2"), "text/plain")},
            )
            v2_id = v2_resp.json()["id"]

            # Switch active back to v1
            patch_resp = await client.patch(
                f"/api/scripts/{script_id}/active-version",
                headers=admin_headers(),
                json={"version_id": v1_id},
            )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["active_version_id"] == v1_id
        assert v2_id != v1_id
