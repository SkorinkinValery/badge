"""Аудиобейдж — FastAPI application entry point."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

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


def _make_stt_engine(active_stt: str) -> object:
    """Instantiate the configured STT engine. FasterWhisper loads model lazily."""
    if active_stt == "faster_whisper":
        from app.adapters.stt.config import WhisperConfig
        from app.adapters.stt.faster_whisper_engine import FasterWhisperEngine
        return FasterWhisperEngine(WhisperConfig())
    if active_stt == "stub":
        from app.adapters.stt.stub_stt import StubSTTEngine
        return StubSTTEngine()
    raise ValueError(f"Unknown active_stt provider: {active_stt!r}. Valid: faster_whisper, stub")


def _make_analyzer(providers: object) -> object:
    """Instantiate the configured LLM analyzer."""
    from app.config.settings import LLMProviderConfig, ProvidersConfig
    cfg: ProvidersConfig = providers  # type: ignore[assignment]
    llm: LLMProviderConfig = cfg.active_llm
    adapter = llm.adapter
    if adapter == "openai_compatible":
        from app.adapters.analyzer.openai_compatible import OpenAICompatibleAnalyzer
        return OpenAICompatibleAnalyzer(llm)
    if adapter == "yandexgpt":
        from app.adapters.analyzer.yandexgpt import YandexGptAnalyzer
        return YandexGptAnalyzer(
            api_key=llm.api_key or "",
            folder_id=getattr(llm, "folder_id", ""),
        )
    if adapter == "gigachat":
        from app.adapters.analyzer.gigachat import GigaChatAnalyzer
        return GigaChatAnalyzer(
            auth_token=llm.api_key or "",
            scope=getattr(llm, "scope", "GIGACHAT_API_PERS"),
        )
    if adapter == "stub":
        from app.adapters.analyzer.stub_analyzer import StubAnalyzer
        return StubAnalyzer()
    raise ValueError(f"Unknown LLM adapter: {adapter!r}. Valid: openai_compatible, yandexgpt, gigachat, stub")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory — parametrisable for tests."""
    _settings = settings or get_settings()

    from app.db.session import init_engine
    session_factory = init_engine(_settings.database_url)

    async def _retention_loop() -> None:
        """Periodic job: purge recordings past their retention_until date."""
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

        from app.services.retention import purge_expired_recordings
        from app.services.storage import ObjectStorage

        factory: async_sessionmaker[AsyncSession] = session_factory
        storage = ObjectStorage(
            endpoint=_settings.minio_endpoint,
            access_key=_settings.minio_root_user,
            secret_key=_settings.minio_root_password,
            bucket=_settings.minio_bucket,
        )
        while True:
            await asyncio.sleep(3600)  # run every hour
            try:
                async with factory() as session, session.begin():
                    result = await purge_expired_recordings(session, storage)
                if result.count:
                    logger.info("retention.purged", count=result.count)
            except Exception as exc:
                logger.error("retention.purge_failed", error=str(exc))

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
        retention_task = asyncio.create_task(_retention_loop())
        logger.info("application_started", debug=_settings.debug)
        try:
            yield
        finally:
            retention_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await retention_task

    app = FastAPI(
        title="Аудиобейдж API",
        description="MVP AI-анализа звонков менеджеров",
        version="0.1.0",
        debug=_settings.debug,
        lifespan=lifespan,
    )
    app.state.settings = _settings
    app.state.session_factory = session_factory

    try:
        from app.services.storage import ObjectStorage
        storage = ObjectStorage(
            endpoint=_settings.minio_endpoint,
            access_key=_settings.minio_root_user,
            secret_key=_settings.minio_root_password,
            bucket=_settings.minio_bucket,
        )
        storage.ensure_bucket()
        app.state.storage = storage
    except Exception as exc:
        logger.error("storage_init_failed", error=str(exc), exc_info=True)
        app.state.storage = None

    # CORS — restrict to configured origins; never wildcard in production
    _cors_origins = getattr(_settings, "cors_origins", ["http://localhost:3000"])
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["Authorization", "Content-Type"],
    )

    # Providers config — CRM + STT + LLM adapter selection
    try:
        from app.config.settings import load_providers_config
        providers = load_providers_config(_settings.providers_yaml_path)
        app.state.crm_config = {
            "active_crm": providers.active_crm,
            "params": providers.crm_params(),
        }
        app.state.stt_engine = _make_stt_engine(providers.active_stt)
        app.state.analyzer = _make_analyzer(providers)
    except Exception as exc:
        logger.error("providers_config_failed", error=str(exc), exc_info=True)
        app.state.crm_config = {"active_crm": "json", "params": {}}
        app.state.stt_engine = _make_stt_engine("stub")
        from app.adapters.analyzer.stub_analyzer import StubAnalyzer
        app.state.analyzer = StubAnalyzer()

    # Override settings dependency to pull from app.state (enables per-app config in tests)
    app.dependency_overrides[get_settings] = _make_get_settings_dep(_settings)

    app.include_router(health_router)

    from app.api.admin import router as admin_router
    from app.api.auth import router as auth_router
    from app.api.kpi import router as kpi_router
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
    app.include_router(kpi_router)
    app.include_router(ws_mic_router)

    return app


# Module-level app instance for uvicorn / ASGI runners
app = create_app()
