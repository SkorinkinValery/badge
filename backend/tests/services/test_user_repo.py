"""Unit/contract tests for UserRepository and auth.login DB flow — B7."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.anyio


# ---------------------------------------------------------------------------
# UserRepository — contract tests against a real AsyncSession mock
# ---------------------------------------------------------------------------


class TestUserRepositoryFindByLogin:
    async def test_returns_none_when_not_found(self) -> None:
        from app.db.repositories.user_repo import UserRepository

        session = AsyncMock()
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=execute_result)

        repo = UserRepository(session)
        result = await repo.find_by_login("nonexistent")
        assert result is None

    async def test_returns_user_when_found(self) -> None:
        from app.db.models.user import UserModel
        from app.db.repositories.user_repo import UserRepository

        session = AsyncMock()
        fake_user = MagicMock(spec=UserModel)
        fake_user.login = "alice"
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = fake_user
        session.execute = AsyncMock(return_value=execute_result)

        repo = UserRepository(session)
        result = await repo.find_by_login("alice")
        assert result is fake_user


class TestUserRepositoryCreateUser:
    async def test_create_user_adds_to_session(self) -> None:
        from app.db.repositories.user_repo import UserRepository

        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        repo = UserRepository(session)
        user = await repo.create_user(
            login="bob",
            password_hash="$argon2id$...",
            role="viewer",
        )

        session.add.assert_called_once_with(user)
        session.flush.assert_awaited_once()
        assert user.login == "bob"
        assert user.role == "viewer"
        assert user.is_active is True
        assert isinstance(user.id, uuid.UUID)

    async def test_create_user_sets_is_active_true(self) -> None:
        from app.db.repositories.user_repo import UserRepository

        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        repo = UserRepository(session)
        user = await repo.create_user(login="carol", password_hash="hash", role="admin")
        assert user.is_active is True


class TestUserRepositoryListUsers:
    async def test_list_returns_all_users(self) -> None:
        from app.db.models.user import UserModel
        from app.db.repositories.user_repo import UserRepository

        session = AsyncMock()
        u1 = MagicMock(spec=UserModel)
        u2 = MagicMock(spec=UserModel)
        scalars_result = MagicMock()
        scalars_result.all.return_value = [u1, u2]
        execute_result = MagicMock()
        execute_result.scalars.return_value = scalars_result
        session.execute = AsyncMock(return_value=execute_result)

        repo = UserRepository(session)
        users = await repo.list_users()
        assert users == [u1, u2]


class TestUserRepositorySetActive:
    async def test_set_active_false_deactivates_user(self) -> None:
        from app.db.models.user import UserModel
        from app.db.repositories.user_repo import UserRepository

        user = MagicMock(spec=UserModel)
        user.is_active = True
        session = AsyncMock()
        session.get = AsyncMock(return_value=user)
        session.flush = AsyncMock()

        repo = UserRepository(session)
        result = await repo.set_active(uuid.uuid4(), is_active=False)

        assert result is user
        assert user.is_active is False

    async def test_set_active_returns_none_if_not_found(self) -> None:
        from app.db.repositories.user_repo import UserRepository

        session = AsyncMock()
        session.get = AsyncMock(return_value=None)

        repo = UserRepository(session)
        result = await repo.set_active(uuid.uuid4(), is_active=False)
        assert result is None


class TestUserRepositoryDelete:
    async def test_delete_returns_true_when_found(self) -> None:
        from app.db.models.user import UserModel
        from app.db.repositories.user_repo import UserRepository

        user = MagicMock(spec=UserModel)
        session = AsyncMock()
        session.get = AsyncMock(return_value=user)
        session.delete = AsyncMock()
        session.flush = AsyncMock()

        repo = UserRepository(session)
        result = await repo.delete(uuid.uuid4())
        assert result is True
        session.delete.assert_awaited_once_with(user)

    async def test_delete_returns_false_when_not_found(self) -> None:
        from app.db.repositories.user_repo import UserRepository

        session = AsyncMock()
        session.get = AsyncMock(return_value=None)

        repo = UserRepository(session)
        result = await repo.delete(uuid.uuid4())
        assert result is False


# ---------------------------------------------------------------------------
# async_seed_admin_if_missing
# ---------------------------------------------------------------------------


class TestAsyncSeedAdmin:
    async def test_seed_creates_user_when_missing(self) -> None:
        from app.services.auth import async_seed_admin_if_missing

        repo = AsyncMock()
        repo.find_by_login = AsyncMock(return_value=None)
        repo.create_user = AsyncMock()

        await async_seed_admin_if_missing(repo, login="admin", password="pw", role="admin")

        repo.create_user.assert_awaited_once()
        call_kwargs = repo.create_user.call_args.kwargs
        assert call_kwargs["login"] == "admin"
        assert call_kwargs["role"] == "admin"
        assert call_kwargs["password_hash"].startswith("$argon2")

    async def test_seed_skips_if_user_exists(self) -> None:
        from app.db.models.user import UserModel
        from app.services.auth import async_seed_admin_if_missing

        existing = MagicMock(spec=UserModel)
        repo = AsyncMock()
        repo.find_by_login = AsyncMock(return_value=existing)
        repo.create_user = AsyncMock()

        await async_seed_admin_if_missing(repo, login="admin", password="pw", role="admin")

        repo.create_user.assert_not_awaited()


# ---------------------------------------------------------------------------
# Login from DB — token contains role from DB record
# ---------------------------------------------------------------------------


def _make_settings() -> object:
    from app.config.settings import Settings

    return Settings(
        DATABASE_URL="postgresql+asyncpg://badge:badge@localhost:5434/badge",
        ADMIN_LOGIN="admin",
        ADMIN_PASSWORD="adminpass",
        JWT_SECRET="testsecret",
        JWT_EXPIRE_MINUTES=60,
    )


class TestLoginFromDB:
    async def test_login_returns_role_from_db(self) -> None:
        """Viewer user logs in → role in token must be 'viewer', not hardcoded 'admin'."""
        from jose import jwt as jose_jwt

        from app.db.models.user import UserModel
        from app.main import create_app
        from app.services.auth import hash_password

        settings = _make_settings()
        app = create_app(settings=settings)  # type: ignore[arg-type]

        fake_viewer = MagicMock(spec=UserModel)
        fake_viewer.login = "alice"
        fake_viewer.role = "viewer"
        fake_viewer.is_active = True
        fake_viewer.password_hash = hash_password("alicepass")

        with patch("app.api.auth.UserRepository") as mock_repo_cls:
            instance = AsyncMock()
            instance.find_by_login = AsyncMock(return_value=fake_viewer)
            mock_repo_cls.return_value = instance

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/auth/login",
                    data={"username": "alice", "password": "alicepass"},
                )

        assert resp.status_code == 200
        payload = jose_jwt.decode(resp.json()["access_token"], "testsecret", algorithms=["HS256"])
        assert payload["sub"] == "alice"
        assert payload["role"] == "viewer"

    async def test_login_fails_for_wrong_password(self) -> None:
        from app.db.models.user import UserModel
        from app.main import create_app
        from app.services.auth import hash_password

        settings = _make_settings()
        app = create_app(settings=settings)  # type: ignore[arg-type]

        fake_user = MagicMock(spec=UserModel)
        fake_user.login = "alice"
        fake_user.role = "viewer"
        fake_user.is_active = True
        fake_user.password_hash = hash_password("correct_pass")

        with patch("app.api.auth.UserRepository") as mock_repo_cls:
            instance = AsyncMock()
            instance.find_by_login = AsyncMock(return_value=fake_user)
            mock_repo_cls.return_value = instance

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/auth/login",
                    data={"username": "alice", "password": "wrong_pass"},
                )

        assert resp.status_code == 401

    async def test_login_fails_for_unknown_user(self) -> None:
        from app.main import create_app

        settings = _make_settings()
        app = create_app(settings=settings)  # type: ignore[arg-type]

        with patch("app.api.auth.UserRepository") as mock_repo_cls:
            instance = AsyncMock()
            instance.find_by_login = AsyncMock(return_value=None)
            mock_repo_cls.return_value = instance

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/auth/login",
                    data={"username": "nobody", "password": "anything"},
                )

        assert resp.status_code == 401

    async def test_login_fails_for_inactive_user(self) -> None:
        from app.db.models.user import UserModel
        from app.main import create_app
        from app.services.auth import hash_password

        settings = _make_settings()
        app = create_app(settings=settings)  # type: ignore[arg-type]

        fake_user = MagicMock(spec=UserModel)
        fake_user.login = "alice"
        fake_user.role = "viewer"
        fake_user.is_active = False
        fake_user.password_hash = hash_password("pass")

        with patch("app.api.auth.UserRepository") as mock_repo_cls:
            instance = AsyncMock()
            instance.find_by_login = AsyncMock(return_value=fake_user)
            mock_repo_cls.return_value = instance

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/auth/login",
                    data={"username": "alice", "password": "pass"},
                )

        assert resp.status_code == 401
