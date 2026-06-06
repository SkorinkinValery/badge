"""Аудиобейдж — FastAPI application entry point."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request

from app.api.health import router as health_router
from app.config.settings import Settings, get_settings

logger = structlog.get_logger(__name__)


async def _seed_admin(session_factory: object, settings: Settings) -> None:
    """Seed admin user from env if not present in DB."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.db.repositories.user_repo import UserRepository
    from app.services.auth import async_seed_admin_if_missing

    factory: async_sessionmaker[AsyncSession] = session_factory  # type: ignore[assignment]
    async with factory() as session, session.begin():
        repo = UserRepository(session)
        await async_seed_admin_if_missing(
            repo,
            login=settings.admin_login,
            password=settings.admin_password,
            role="admin",
        )


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
        try:
            await _seed_admin(session_factory, _settings)
            logger.info("admin_seeded_ok")
        except Exception as exc:
            logger.warning("admin_seed_failed", error=str(exc))
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

    # CRM config — mutable in-memory state (GET/PUT /api/admin/settings)
    try:
        from app.config.settings import load_providers_config
        providers = load_providers_config(_settings.providers_yaml_path)
        app.state.crm_config = {
            "active_crm": providers.active_crm,
            "params": providers.crm_params(),
        }
    except Exception:
        app.state.crm_config = {"active_crm": "json", "params": {}}

    # Override settings dependency to pull from app.state (enables per-app config in tests)
    app.dependency_overrides[get_settings] = _make_get_settings_dep(_settings)

    app.include_router(health_router)

    from app.api.admin import router as admin_router
    from app.api.auth import router as auth_router
    from app.api.managers import router as managers_router
    from app.api.recordings import router as recordings_router
    from app.api.scripts import router as scripts_router
    from app.api.uploads import router as uploads_router
    from app.api.users import router as users_router
    from app.api.ws_mic import router as ws_mic_router
    app.include_router(auth_router)
    app.include_router(uploads_router)
    app.include_router(recordings_router)
    app.include_router(managers_router)
    app.include_router(scripts_router)
    app.include_router(admin_router)
    app.include_router(users_router)
    app.include_router(ws_mic_router)

    return app


# Module-level app instance for uvicorn / ASGI runners
app = create_app()
