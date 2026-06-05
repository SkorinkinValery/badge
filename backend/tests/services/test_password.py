"""Unit tests for password hashing and user seeding — M5-T1."""

from __future__ import annotations

import pytest


class TestPasswordHashing:
    def test_hash_returns_string(self) -> None:
        from app.services.auth import hash_password

        result = hash_password("secret123")
        assert isinstance(result, str)

    def test_verify_correct_password(self) -> None:
        from app.services.auth import hash_password, verify_password

        hashed = hash_password("secret123")
        assert verify_password("secret123", hashed) is True

    def test_verify_wrong_password(self) -> None:
        from app.services.auth import hash_password, verify_password

        hashed = hash_password("secret123")
        assert verify_password("wrong", hashed) is False

    def test_hash_is_non_deterministic(self) -> None:
        from app.services.auth import hash_password

        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2

    def test_hash_uses_argon2_prefix(self) -> None:
        from app.services.auth import hash_password

        result = hash_password("password")
        assert result.startswith("$argon2")


class TestUserRoleEnum:
    def test_admin_role_value(self) -> None:
        from app.services.auth import UserRole

        assert UserRole.ADMIN.value == "admin"

    def test_viewer_role_value(self) -> None:
        from app.services.auth import UserRole

        assert UserRole.VIEWER.value == "viewer"

    def test_role_from_string(self) -> None:
        from app.services.auth import UserRole

        assert UserRole("admin") is UserRole.ADMIN
        assert UserRole("viewer") is UserRole.VIEWER

    def test_invalid_role_raises(self) -> None:
        from app.services.auth import UserRole

        with pytest.raises(ValueError):
            UserRole("superuser")


class TestAdminSeeding:
    def test_seed_admin_idempotent(self) -> None:
        from unittest.mock import MagicMock
        from app.services.auth import seed_admin_if_missing

        repo = MagicMock()
        repo.find_by_login.return_value = None
        seed_admin_if_missing(repo, login="admin", password="pw", role="admin")
        repo.create_user.assert_called_once()

    def test_seed_admin_skips_if_exists(self) -> None:
        from unittest.mock import MagicMock
        from app.services.auth import seed_admin_if_missing

        repo = MagicMock()
        repo.find_by_login.return_value = object()
        seed_admin_if_missing(repo, login="admin", password="pw", role="admin")
        repo.create_user.assert_not_called()
