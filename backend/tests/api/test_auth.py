"""API tests for POST /api/auth/login — M5-T2."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.anyio


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
        JWT_SECRET="testsecret",
        JWT_EXPIRE_MINUTES=60,
    )
    return create_app(settings=settings)


async def test_login_valid_credentials_returns_200(test_app) -> None:  # type: ignore[no-untyped-def]
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/auth/login",
            data={"username": "admin", "password": "adminpass123"},
        )
    assert resp.status_code == 200


async def test_login_returns_access_token(test_app) -> None:  # type: ignore[no-untyped-def]
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/auth/login",
            data={"username": "admin", "password": "adminpass123"},
        )
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


async def test_login_token_contains_sub_and_role(test_app) -> None:  # type: ignore[no-untyped-def]
    from jose import jwt as jose_jwt

    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/auth/login",
            data={"username": "admin", "password": "adminpass123"},
        )
    token = resp.json()["access_token"]
    payload = jose_jwt.decode(token, "testsecret", algorithms=["HS256"])
    assert payload["sub"] == "admin"
    assert payload["role"] == "admin"


async def test_login_wrong_password_returns_401(test_app) -> None:  # type: ignore[no-untyped-def]
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/auth/login",
            data={"username": "admin", "password": "wrongpassword"},
        )
    assert resp.status_code == 401


async def test_login_unknown_user_returns_401(test_app) -> None:  # type: ignore[no-untyped-def]
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/auth/login",
            data={"username": "nobody", "password": "anything"},
        )
    assert resp.status_code == 401


async def test_expired_token_raises_on_decode(test_app) -> None:  # type: ignore[no-untyped-def]
    from datetime import UTC, datetime, timedelta

    from jose import JWTError
    from jose import jwt as jose_jwt

    expired_token = jose_jwt.encode(
        {"sub": "admin", "role": "admin", "exp": datetime.now(tz=UTC) - timedelta(hours=1)},
        "testsecret",
        algorithm="HS256",
    )
    with pytest.raises(JWTError):
        jose_jwt.decode(expired_token, "testsecret", algorithms=["HS256"])
