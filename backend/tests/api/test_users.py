"""API tests for /api/admin/users and role guard (B7)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

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


def _headers(role: str = "admin") -> dict[str, str]:
    return {"Authorization": f"Bearer {_make_token('testuser', role)}"}


@pytest.fixture
def test_app() -> object:
    from app.config.settings import Settings
    from app.main import create_app

    settings = Settings(
        DATABASE_URL="postgresql+asyncpg://badge:badge@localhost:5434/badge",
        ADMIN_LOGIN="admin",
        ADMIN_PASSWORD="adminpass",
        JWT_SECRET=_JWT_SECRET,
        JWT_EXPIRE_MINUTES=60,
    )
    return create_app(settings=settings)


def _make_user_model(
    login: str = "alice",
    role: str = "viewer",
    is_active: bool = True,
) -> object:
    from app.db.models.user import UserModel

    user = MagicMock(spec=UserModel)
    user.id = uuid.uuid4()
    user.login = login
    user.role = role
    user.is_active = is_active
    return user


# ---------------------------------------------------------------------------
# Role guard tests — viewer must be blocked from admin endpoints
# ---------------------------------------------------------------------------


class TestRoleGuardAdminUsers:
    async def test_viewer_cannot_list_users(self, test_app: object) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/admin/users",
                headers=_headers(role="viewer"),
            )
        assert resp.status_code == 403

    async def test_viewer_cannot_create_user(self, test_app: object) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/admin/users",
                headers=_headers(role="viewer"),
                json={"login": "x", "password": "y"},
            )
        assert resp.status_code == 403

    async def test_viewer_cannot_patch_user(self, test_app: object) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.patch(
                f"/api/admin/users/{uuid.uuid4()}",
                headers=_headers(role="viewer"),
                json={"is_active": False},
            )
        assert resp.status_code == 403

    async def test_viewer_cannot_delete_user(self, test_app: object) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.delete(
                f"/api/admin/users/{uuid.uuid4()}",
                headers=_headers(role="viewer"),
            )
        assert resp.status_code == 403

    async def test_no_token_returns_401(self, test_app: object) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/admin/users")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Admin contract tests for /api/admin/users (with mocked repo)
# ---------------------------------------------------------------------------


class TestAdminUsersListContract:
    async def test_list_returns_users_without_password_hash(
        self, test_app: object
    ) -> None:
        user1 = _make_user_model(login="alice", role="viewer", is_active=True)
        user2 = _make_user_model(login="bob", role="admin", is_active=False)

        with patch("app.api.users.UserRepository") as mock_repo_cls:
            instance = AsyncMock()
            instance.list_users = AsyncMock(return_value=[user1, user2])
            mock_repo_cls.return_value = instance

            async with AsyncClient(
                transport=ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                resp = await client.get(
                    "/api/admin/users", headers=_headers(role="admin")
                )

        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 2
        for item in body:
            assert "password_hash" not in item
            assert "id" in item
            assert "login" in item
            assert "role" in item
            assert "is_active" in item


class TestAdminUsersCreateContract:
    async def test_create_returns_201_with_user_out(self, test_app: object) -> None:
        from app.db.models.user import UserModel

        new_user_id = uuid.uuid4()

        with patch("app.api.users.UserRepository") as mock_repo_cls, \
             patch("app.api.users.hash_password", return_value="$argon2id$fake"):
            instance = AsyncMock()
            instance.find_by_login = AsyncMock(return_value=None)

            # Return a real-ish object that session.refresh won't choke on
            # We patch session.commit and session.refresh to be no-ops
            real_user = MagicMock(spec=UserModel)
            real_user.id = new_user_id
            real_user.login = "charlie"
            real_user.role = "viewer"
            real_user.is_active = True
            instance.create_user = AsyncMock(return_value=real_user)
            mock_repo_cls.return_value = instance

            with patch("sqlalchemy.ext.asyncio.AsyncSession.commit", new_callable=AsyncMock), \
                 patch("sqlalchemy.ext.asyncio.AsyncSession.refresh", new_callable=AsyncMock):
                async with AsyncClient(
                    transport=ASGITransport(app=test_app), base_url="http://test"
                ) as client:
                    resp = await client.post(
                        "/api/admin/users",
                        headers=_headers(role="admin"),
                        json={"login": "charlie", "password": "secret123"},
                    )

        assert resp.status_code == 201
        body = resp.json()
        assert body["login"] == "charlie"
        assert "password_hash" not in body

    async def test_create_returns_409_for_duplicate_login(
        self, test_app: object
    ) -> None:
        existing = _make_user_model(login="charlie")

        with patch("app.api.users.UserRepository") as mock_repo_cls:
            instance = AsyncMock()
            instance.find_by_login = AsyncMock(return_value=existing)
            mock_repo_cls.return_value = instance

            async with AsyncClient(
                transport=ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/admin/users",
                    headers=_headers(role="admin"),
                    json={"login": "charlie", "password": "secret123"},
                )

        assert resp.status_code == 409


class TestAdminUsersPatchContract:
    async def test_patch_returns_404_for_nonexistent(self, test_app: object) -> None:
        """PATCH with unknown UUID returns 404 (session.get returns None)."""
        with patch("app.api.users.UserRepository"), \
             patch("sqlalchemy.ext.asyncio.AsyncSession.get", new_callable=AsyncMock, return_value=None):
            async with AsyncClient(
                transport=ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                resp = await client.patch(
                    f"/api/admin/users/{uuid.uuid4()}",
                    headers=_headers(role="admin"),
                    json={"is_active": False},
                )
        assert resp.status_code == 404


class TestAdminUsersDeleteContract:
    async def test_delete_returns_404_for_nonexistent(self, test_app: object) -> None:
        with patch("app.api.users.UserRepository") as mock_repo_cls:
            instance = AsyncMock()
            instance.delete = AsyncMock(return_value=False)
            mock_repo_cls.return_value = instance

            async with AsyncClient(
                transport=ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                resp = await client.delete(
                    f"/api/admin/users/{uuid.uuid4()}",
                    headers=_headers(role="admin"),
                )

        assert resp.status_code == 404

    async def test_delete_returns_204_for_existing(self, test_app: object) -> None:
        with patch("app.api.users.UserRepository") as mock_repo_cls:
            instance = AsyncMock()
            instance.delete = AsyncMock(return_value=True)
            mock_repo_cls.return_value = instance

            async with AsyncClient(
                transport=ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                resp = await client.delete(
                    f"/api/admin/users/{uuid.uuid4()}",
                    headers=_headers(role="admin"),
                )

        assert resp.status_code == 204
