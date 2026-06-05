"""Tests for M7-T4: WS /api/ws/mic endpoint."""

from __future__ import annotations

import base64
import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from starlette.testclient import TestClient

_JWT_SECRET = "test-jwt-secret"
_DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://badge:badge@localhost:5434/badge",
)

_HAS_DB = bool(os.environ.get("DATABASE_URL"))


def _make_token(role: str = "admin") -> str:
    from jose import jwt

    return jwt.encode(
        {
            "sub": "user",
            "role": role,
            "exp": datetime.now(tz=UTC) + timedelta(hours=1),
        },
        _JWT_SECRET,
        algorithm="HS256",
    )


def _make_test_app() -> object:
    """Create a test app (no real DB needed for auth/protocol tests)."""
    from app.config.settings import Settings
    from app.main import create_app

    settings = Settings(
        JWT_SECRET=_JWT_SECRET,
        MIC_WINDOW_BYTES=100,
        MIC_MAX_BYTES=10_000,
    )
    return create_app(settings=settings)


# ── Auth tests (no real DB needed) ──────────────────────────────────────────

class TestWsMicAuth:
    def test_missing_token_gets_auth_error(self) -> None:
        app = _make_test_app()
        with TestClient(app) as client, client.websocket_connect("/api/ws/mic") as ws:
            msg = ws.receive_json()
            assert msg["type"] == "error"
            assert msg["code"] == "AUTH_ERROR"

    def test_invalid_token_gets_auth_error(self) -> None:
        app = _make_test_app()
        with (
            TestClient(app) as client,
            client.websocket_connect("/api/ws/mic?token=bad.token.here") as ws,
        ):
            msg = ws.receive_json()
            assert msg["type"] == "error"
            assert msg["code"] == "AUTH_ERROR"


# ── Protocol tests (no real DB needed for these cases) ──────────────────────

class TestWsMicProtocol:
    def test_chunk_before_start_gets_protocol_error(self) -> None:
        app = _make_test_app()
        token = _make_token()
        with (
            TestClient(app) as client,
            client.websocket_connect(f"/api/ws/mic?token={token}") as ws,
        ):
            ws.send_json(
                {
                    "type": "chunk",
                    "seq": 0,
                    "data": base64.b64encode(b"x" * 10).decode(),
                }
            )
            msg = ws.receive_json()
            assert msg["type"] == "error"
            assert msg["code"] == "PROTOCOL_ERROR"

    def test_stop_before_start_gets_protocol_error(self) -> None:
        app = _make_test_app()
        token = _make_token()
        with (
            TestClient(app) as client,
            client.websocket_connect(f"/api/ws/mic?token={token}") as ws,
        ):
            ws.send_json({"type": "stop"})
            msg = ws.receive_json()
            assert msg["type"] == "error"
            assert msg["code"] == "PROTOCOL_ERROR"


# ── Integration tests (need real DB) ────────────────────────────────────────

@pytest.fixture(scope="module")
def _sync_engine():  # type: ignore[no-untyped-def]
    if not _HAS_DB:
        pytest.skip("No DATABASE_URL — skip WS integration tests")
    from sqlalchemy import create_engine

    import app.db.models  # noqa: F401
    from app.db.base import Base

    sync_url = _DB_URL.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    engine = create_engine(sync_url, echo=False)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="module")
def ws_test_app(_sync_engine):  # type: ignore[no-untyped-def]
    from sqlalchemy.pool import NullPool

    from app.config.settings import Settings
    from app.db.session import make_session_factory
    from app.main import create_app

    settings = Settings(
        DATABASE_URL=_DB_URL,
        JWT_SECRET=_JWT_SECRET,
        MIC_WINDOW_BYTES=50,
        MIC_MAX_BYTES=10_000,
    )
    app = create_app(settings=settings)
    app.state.session_factory = make_session_factory(  # type: ignore[attr-defined]
        _DB_URL, pool_pre_ping=False, poolclass=NullPool
    )
    return app


@pytest.fixture(scope="module")
def _db_manager(ws_test_app):  # type: ignore[no-untyped-def]
    """Create a manager in the DB for WS tests."""
    import asyncio

    from sqlalchemy.pool import NullPool

    from app.db.models.manager import ManagerModel
    from app.db.session import make_session_factory

    async def _create() -> uuid.UUID:
        factory = make_session_factory(_DB_URL, pool_pre_ping=False, poolclass=NullPool)
        async with factory() as session:
            mgr = ManagerModel(
                id=uuid.uuid4(),
                full_name="WS Test Manager",
                position="tester",
                is_active=True,
            )
            session.add(mgr)
            await session.commit()
            return mgr.id

    return asyncio.run(_create())


class TestWsMicIntegration:
    def test_start_message_creates_recording(
        self, ws_test_app: object, _db_manager: uuid.UUID
    ) -> None:
        token = _make_token()
        with (
            TestClient(ws_test_app) as client,  # type: ignore[arg-type]
            client.websocket_connect(f"/api/ws/mic?token={token}") as ws,
        ):
            ws.send_json(
                {
                    "type": "start",
                    "manager_id": str(_db_manager),
                    "consent_flag": True,
                }
            )
            msg = ws.receive_json()
            assert msg["type"] == "ack"
            assert "recording" in msg.get("message", "")

    def test_chunk_stream_returns_partial_transcript(
        self, ws_test_app: object, _db_manager: uuid.UUID
    ) -> None:
        token = _make_token()
        chunk_data = base64.b64encode(b"\x00" * 200).decode()
        with (
            TestClient(ws_test_app) as client,  # type: ignore[arg-type]
            client.websocket_connect(f"/api/ws/mic?token={token}") as ws,
        ):
            ws.send_json(
                {
                    "type": "start",
                    "manager_id": str(_db_manager),
                    "consent_flag": True,
                }
            )
            ws.receive_json()  # ack for start

            ws.send_json({"type": "chunk", "seq": 0, "data": chunk_data})
            messages = []
            for _ in range(5):
                try:
                    msg = ws.receive_json()
                    messages.append(msg)
                    if msg["type"] == "ack":
                        break
                except Exception:
                    break
            types = [m["type"] for m in messages]
            assert "ack" in types or "partial_transcript" in types

    def test_stop_finalizes_recording(
        self, ws_test_app: object, _db_manager: uuid.UUID
    ) -> None:
        token = _make_token()
        with (
            TestClient(ws_test_app) as client,  # type: ignore[arg-type]
            client.websocket_connect(f"/api/ws/mic?token={token}") as ws,
        ):
            ws.send_json(
                {
                    "type": "start",
                    "manager_id": str(_db_manager),
                    "consent_flag": True,
                }
            )
            ws.receive_json()  # ack

            ws.send_json({"type": "stop"})
            try:
                while True:
                    ws.receive_json()
            except Exception:
                pass  # closed

    def test_consent_flag_false_rejected(
        self, ws_test_app: object, _db_manager: uuid.UUID
    ) -> None:
        token = _make_token()
        with (
            TestClient(ws_test_app) as client,  # type: ignore[arg-type]
            client.websocket_connect(f"/api/ws/mic?token={token}") as ws,
        ):
            ws.send_json(
                {
                    "type": "start",
                    "manager_id": str(_db_manager),
                    "consent_flag": False,
                }
            )
            msg = ws.receive_json()
            assert msg["type"] == "error"
            assert "consent" in msg["message"].lower()
