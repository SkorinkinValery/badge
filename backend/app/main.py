"""Аудиобейдж — FastAPI application entry point."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from app.api.health import router as health_router
from app.config.settings import Settings, get_settings

logger = structlog.get_logger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory — parametrisable for tests."""
    _settings = settings or get_settings()

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

    app.include_router(health_router)

    return app


# Module-level app instance for uvicorn / ASGI runners
app = create_app()
