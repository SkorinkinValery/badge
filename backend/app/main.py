"""Аудиобейдж — FastAPI application entry point."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request

from app.api.health import router as health_router
from app.config.settings import Settings, get_settings

logger = structlog.get_logger(__name__)


def _make_get_settings_dep(settings: Settings):  # type: ignore[no-untyped-def]
    def _get_settings(request: Request) -> Settings:
        return request.app.state.settings  # type: ignore[no-any-return]
    return _get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory — parametrisable for tests."""
    _settings = settings or get_settings()

    from app.db.session import init_engine
    session_factory = init_engine(_settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        structlog.configure(
            processors=[
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.stdlib.add_log_level,
                structlog.dev.ConsoleRenderer(),
            ],
        )
        logger.info("application_started", debug=_settings.debug)
        yield

    app = FastAPI(
        title="Аудиобейдж API",
        description="MVP AI-анализа звонков менеджеров",
        version="0.1.0",
        debug=_settings.debug,
        lifespan=lifespan,
    )
    app.state.settings = _settings
    app.state.session_factory = session_factory

    # Override settings dependency to pull from app.state (enables per-app config in tests)
    app.dependency_overrides[get_settings] = _make_get_settings_dep(_settings)

    app.include_router(health_router)

    from app.api.recordings import router as recordings_router
    from app.api.uploads import router as uploads_router
    app.include_router(uploads_router)
    app.include_router(recordings_router)

    return app


# Module-level app instance for uvicorn / ASGI runners
app = create_app()
