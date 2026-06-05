"""Application settings via pydantic-settings + providers.yaml loader."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

# Default path to providers.yaml — can be overridden in tests or deployment
_DEFAULT_PROVIDERS_PATH = (
    Path(__file__).parent.parent.parent.parent / "infra" / "config" / "providers.yaml"
)


class LLMProviderConfig(BaseModel):
    """Active LLM provider configuration."""

    adapter: str = "openai_compatible"
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    # api_key comes from env (LLM_API_KEY), never stored in yaml
    api_key: str | None = None


class ProvidersConfig(BaseModel):
    """Typed representation of providers.yaml."""

    active_stt: str = "faster_whisper"
    active_llm: LLMProviderConfig = Field(default_factory=LLMProviderConfig)
    active_crm: str = "json"
    default_language: str = "ru"


def load_providers_config(
    providers_path: Path = _DEFAULT_PROVIDERS_PATH,
    env_overrides: dict[str, str] | None = None,
) -> ProvidersConfig:
    """Load and validate providers.yaml; merge api_key from env/overrides."""
    with open(providers_path) as f:
        raw: dict[object, object] = yaml.safe_load(f) or {}

    cfg = ProvidersConfig.model_validate(raw)

    # api_key never lives in yaml — read from env or provided overrides
    api_key = (env_overrides or {}).get("LLM_API_KEY") or os.environ.get("LLM_API_KEY") or ""
    cfg.active_llm.api_key = api_key or None

    return cfg


class Settings(BaseSettings):
    """Application settings, read from environment variables."""

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://badge:badge@localhost:5432/badge",
        alias="DATABASE_URL",
    )

    # MinIO
    minio_endpoint: str = Field(default="http://localhost:9000", alias="MINIO_ENDPOINT")
    minio_bucket: str = Field(default="audio", alias="MINIO_BUCKET")
    minio_root_user: str = Field(default="minioadmin", alias="MINIO_ROOT_USER")
    minio_root_password: str = Field(default="minioadmin", alias="MINIO_ROOT_PASSWORD")

    # Application
    secret_key: str = Field(default="changeme", alias="SECRET_KEY")
    debug: bool = Field(default=False, alias="DEBUG")

    # Path to providers.yaml
    providers_yaml_path: Path = Field(
        default=_DEFAULT_PROVIDERS_PATH,
        alias="PROVIDERS_YAML_PATH",
    )

    model_config = {"populate_by_name": True, "extra": "ignore"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings (singleton)."""
    return Settings()
