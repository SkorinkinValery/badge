"""Tests that create_app initialises app.state.stt_engine correctly (bug fix)."""

from __future__ import annotations

import pytest


class TestMakeSttEngine:
    def test_stub_mode_returns_stub(self) -> None:
        from app.adapters.stt.stub_stt import StubSTTEngine
        from app.main import _make_stt_engine

        engine = _make_stt_engine("stub")
        assert isinstance(engine, StubSTTEngine)

    def test_unknown_mode_raises_value_error(self) -> None:
        """Unknown providers must fail loudly, not silently fall back to a stub (W1)."""
        from app.main import _make_stt_engine

        with pytest.raises(ValueError, match="Unknown active_stt provider"):
            _make_stt_engine("nonexistent_provider")

    def test_faster_whisper_mode_returns_whisper_engine(self) -> None:
        from app.adapters.stt.faster_whisper_engine import FasterWhisperEngine
        from app.main import _make_stt_engine

        engine = _make_stt_engine("faster_whisper")
        assert isinstance(engine, FasterWhisperEngine)

    def test_create_app_sets_stt_engine_on_state(self) -> None:
        from app.config.settings import Settings
        from app.main import create_app

        settings = Settings(JWT_SECRET="test")
        app = create_app(settings=settings)
        assert hasattr(app.state, "stt_engine")
        assert app.state.stt_engine is not None

    def test_create_app_stt_engine_is_not_stub_by_default(self) -> None:
        """Default providers.yaml has active_stt=faster_whisper — must not be StubSTTEngine."""
        from app.adapters.stt.stub_stt import StubSTTEngine
        from app.config.settings import Settings
        from app.main import create_app

        settings = Settings(JWT_SECRET="test")
        app = create_app(settings=settings)
        assert not isinstance(app.state.stt_engine, StubSTTEngine)
