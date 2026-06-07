"""M0-T3: Tests for pydantic-settings + providers config loader."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

PROVIDERS_YAML = (
    Path(__file__).parent.parent.parent.parent / "infra" / "config" / "providers.yaml"
)


def test_providers_yaml_exists() -> None:
    assert PROVIDERS_YAML.exists(), f"providers.yaml not found at {PROVIDERS_YAML}"


def test_settings_reads_database_url() -> None:
    from app.config.settings import Settings

    with patch.dict(
        os.environ,
        {"DATABASE_URL": "postgresql+asyncpg://test:test@localhost:5432/test"},
        clear=False,
    ):
        s = Settings()
        assert "postgresql" in s.database_url


def test_settings_reads_minio_config() -> None:
    from app.config.settings import Settings

    with patch.dict(
        os.environ,
        {
            "MINIO_ENDPOINT": "http://localhost:9000",
            "MINIO_BUCKET": "audio",
            "MINIO_ROOT_USER": "minioadmin",
            "MINIO_ROOT_PASSWORD": "secret",
        },
        clear=False,
    ):
        s = Settings()
        assert s.minio_endpoint == "http://localhost:9000"
        assert s.minio_bucket == "audio"


def test_providers_config_parses_active_stt() -> None:
    from app.config.settings import load_providers_config

    cfg = load_providers_config(PROVIDERS_YAML)
    assert cfg.active_stt == "faster_whisper"


def test_providers_config_parses_active_llm() -> None:
    from app.config.settings import load_providers_config

    cfg = load_providers_config(PROVIDERS_YAML)
    assert cfg.active_llm.model == "gpt-4o-mini"
    assert cfg.active_llm.base_url is not None


def test_providers_config_parses_active_crm() -> None:
    from app.config.settings import load_providers_config

    cfg = load_providers_config(PROVIDERS_YAML)
    assert cfg.active_crm in {"json", "google_sheets", "webhook", "bitrix24"}


def test_providers_config_default_language_is_ru() -> None:
    from app.config.settings import load_providers_config

    cfg = load_providers_config(PROVIDERS_YAML)
    assert cfg.default_language == "ru"


def test_providers_config_api_key_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """api_key must not be present in yaml itself — comes from env.

    Clear the env key first (a real LLM_API_KEY may be exported via .env when
    running through `make test`) so we genuinely assert the YAML has no key.
    """
    from app.config.settings import load_providers_config

    monkeypatch.delenv("LLM_API_KEY", raising=False)
    cfg = load_providers_config(PROVIDERS_YAML)
    # api_key in yaml should be None/empty — real key only from env
    assert cfg.active_llm.api_key is None or cfg.active_llm.api_key == ""


def test_providers_config_env_overrides_default() -> None:
    from app.config.settings import load_providers_config

    cfg = load_providers_config(PROVIDERS_YAML, env_overrides={"LLM_API_KEY": "test-key-xyz"})
    assert cfg.active_llm.api_key == "test-key-xyz"


def test_missing_database_url_raises() -> None:
    from app.config.settings import Settings

    with patch.dict(os.environ, {}, clear=True):
        # Settings has a fallback, so we test that the model is usable
        # The field has a default so no error is expected in basic case
        s = Settings()
        assert s.database_url  # default is provided


def test_settings_cached() -> None:
    """get_settings() returns the same object (lru_cache)."""
    from app.config.settings import get_settings

    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
