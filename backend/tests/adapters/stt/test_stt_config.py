"""Unit tests for WhisperConfig — M3-T1."""

from __future__ import annotations

import pytest
from pydantic import ValidationError


class TestWhisperConfigDefaults:
    def test_defaults_model_size(self) -> None:
        from app.adapters.stt.config import WhisperConfig
        cfg = WhisperConfig()
        assert cfg.model_size in {"large-v3", "medium", "small", "base", "tiny"}

    def test_default_device_is_cpu(self) -> None:
        from app.adapters.stt.config import WhisperConfig
        cfg = WhisperConfig()
        assert cfg.device == "cpu"

    def test_default_language_is_ru(self) -> None:
        from app.adapters.stt.config import WhisperConfig
        cfg = WhisperConfig()
        assert cfg.default_language == "ru"

    def test_default_vad_filter_is_true(self) -> None:
        from app.adapters.stt.config import WhisperConfig
        cfg = WhisperConfig()
        assert cfg.vad_filter is True

    def test_default_initial_prompt_is_none(self) -> None:
        from app.adapters.stt.config import WhisperConfig
        cfg = WhisperConfig()
        assert cfg.initial_prompt is None

    def test_default_compute_type_is_int8(self) -> None:
        from app.adapters.stt.config import WhisperConfig
        cfg = WhisperConfig()
        assert cfg.compute_type == "int8"


class TestWhisperConfigParsing:
    def test_model_size_large_v3(self) -> None:
        from app.adapters.stt.config import WhisperConfig
        cfg = WhisperConfig(model_size="large-v3")
        assert cfg.model_size == "large-v3"

    def test_model_size_medium(self) -> None:
        from app.adapters.stt.config import WhisperConfig
        cfg = WhisperConfig(model_size="medium")
        assert cfg.model_size == "medium"

    def test_device_cuda(self) -> None:
        from app.adapters.stt.config import WhisperConfig
        cfg = WhisperConfig(device="cuda")
        assert cfg.device == "cuda"

    def test_device_cpu(self) -> None:
        from app.adapters.stt.config import WhisperConfig
        cfg = WhisperConfig(device="cpu")
        assert cfg.device == "cpu"

    def test_initial_prompt_set(self) -> None:
        from app.adapters.stt.config import WhisperConfig
        cfg = WhisperConfig(initial_prompt="Привет, клиент")
        assert cfg.initial_prompt == "Привет, клиент"

    def test_vad_filter_false(self) -> None:
        from app.adapters.stt.config import WhisperConfig
        cfg = WhisperConfig(vad_filter=False)
        assert cfg.vad_filter is False


class TestWhisperConfigValidation:
    def test_invalid_device_raises(self) -> None:
        from app.adapters.stt.config import WhisperConfig
        with pytest.raises(ValidationError):
            WhisperConfig(device="tpu")

    def test_invalid_model_size_raises(self) -> None:
        from app.adapters.stt.config import WhisperConfig
        with pytest.raises(ValidationError):
            WhisperConfig(model_size="giga-v9")


class TestSttProviderBaseConfig:
    def test_base_config_importable(self) -> None:
        from app.adapters.stt.config import SttProviderConfig  # noqa: F401

    def test_whisper_is_stt_provider(self) -> None:
        from app.adapters.stt.config import SttProviderConfig, WhisperConfig
        cfg = WhisperConfig()
        assert isinstance(cfg, SttProviderConfig)
