"""Auth service: password hashing (argon2), role enum, admin seeding, JWT utilities."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any, Protocol

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jose import jwt as jose_jwt

_ph = PasswordHasher()

_JWT_ALGORITHM = "HS256"


class UserRole(StrEnum):
    ADMIN = "admin"
    VIEWER = "viewer"


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, plain)
    except VerifyMismatchError:
        return False


def create_access_token(sub: str, role: str, secret: str, expire_minutes: int) -> str:
    exp = datetime.now(tz=UTC) + timedelta(minutes=expire_minutes)
    return jose_jwt.encode(
        {"sub": sub, "role": role, "exp": exp},
        secret,
        algorithm=_JWT_ALGORITHM,
    )


def decode_token(token: str, secret: str) -> dict[str, Any]:
    return jose_jwt.decode(token, secret, algorithms=[_JWT_ALGORITHM])


class UserRepo(Protocol):
    def find_by_login(self, login: str) -> Any | None: ...
    def create_user(self, login: str, password_hash: str, role: str) -> Any: ...


def seed_admin_if_missing(repo: UserRepo, login: str, password: str, role: str) -> None:
    if repo.find_by_login(login) is not None:
        return
    repo.create_user(login=login, password_hash=hash_password(password), role=role)


class AsyncUserRepo(Protocol):
    async def find_by_login(self, login: str) -> Any | None: ...
    async def create_user(self, login: str, password_hash: str, role: str) -> Any: ...


async def async_seed_admin_if_missing(
    repo: AsyncUserRepo, login: str, password: str, role: str
) -> None:
    """Async variant of seed_admin_if_missing for use in async lifespans."""
    if await repo.find_by_login(login) is not None:
        return
    await repo.create_user(login=login, password_hash=hash_password(password), role=role)
