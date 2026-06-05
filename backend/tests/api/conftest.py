"""Shared fixtures for API tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

_JWT_SECRET = "test-jwt-secret"
_JWT_ALG = "HS256"


def make_admin_token(secret: str = _JWT_SECRET) -> str:
    from jose import jwt as jose_jwt

    return jose_jwt.encode(
        {
            "sub": "admin",
            "role": "admin",
            "exp": datetime.now(tz=UTC) + timedelta(hours=1),
        },
        secret,
        algorithm=_JWT_ALG,
    )


def admin_headers(secret: str = _JWT_SECRET) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_admin_token(secret)}"}
