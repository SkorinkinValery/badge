"""STT provider configuration models — M3-T1."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class SttProviderConfig(BaseModel):
    """Base config for any STT provider (Whisper, Yandex, Sber, …)."""

    default_language: str = "ru"


_ALLOWED_DEVICES = {"cpu", "cuda"}
_ALLOWED_MODEL_SIZES = {"tiny", "base", "small", "medium", "large-v1", "large-v2", "large-v3"}


class WhisperConfig(SttProviderConfig):
    """Configuration for FasterWhisperEngine."""

    model_size: Literal["tiny", "base", "small", "medium", "large-v1", "large-v2", "large-v3"] = (
        "medium"
    )
    device: Literal["cpu", "cuda"] = "cpu"
    compute_type: str = "int8"
    vad_filter: bool = True
    initial_prompt: str | None = None
    vocabulary: list[str] = []
