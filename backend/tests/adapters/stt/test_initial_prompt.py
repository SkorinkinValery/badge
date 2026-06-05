"""Unit tests for initial_prompt/vocabulary config-driven behaviour — M3-T5."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from app.core.ports.audio_source import AudioPayload


def _make_payload() -> AudioPayload:
    return AudioPayload(
        audio_data=b"\x00" * 100,
        sample_rate=16000,
        manager_id=uuid.uuid4(),
        channel="file",
        started_at=datetime.now(tz=UTC),
        consent_flag=True,
    )


class TestInitialPromptPassthrough:
    def test_initial_prompt_passed_to_transcribe(self) -> None:
        from app.adapters.stt.config import WhisperConfig
        from app.adapters.stt.faster_whisper_engine import FasterWhisperEngine

        cfg = WhisperConfig(initial_prompt="Менеджер продаж Иван")
        engine = FasterWhisperEngine(cfg)

        with patch.object(engine, "_load_model") as mock_load:
            mock_model = MagicMock()
            mock_info = MagicMock()
            mock_info.language = "ru"
            mock_model.transcribe.return_value = (iter([]), mock_info)
            mock_load.return_value = mock_model

            engine.transcribe(_make_payload())

            call_kwargs = mock_model.transcribe.call_args
            assert call_kwargs is not None
            prompt = call_kwargs.kwargs.get("initial_prompt") or (
                call_kwargs.args[1] if len(call_kwargs.args) > 1 else None
            )
            assert "Менеджер продаж Иван" in (prompt or "")

    def test_no_initial_prompt_passes_none(self) -> None:
        from app.adapters.stt.config import WhisperConfig
        from app.adapters.stt.faster_whisper_engine import FasterWhisperEngine

        cfg = WhisperConfig(initial_prompt=None, vocabulary=[])
        engine = FasterWhisperEngine(cfg)

        with patch.object(engine, "_load_model") as mock_load:
            mock_model = MagicMock()
            mock_info = MagicMock()
            mock_info.language = "ru"
            mock_model.transcribe.return_value = (iter([]), mock_info)
            mock_load.return_value = mock_model

            engine.transcribe(_make_payload())

            call_kwargs = mock_model.transcribe.call_args
            prompt = call_kwargs.kwargs.get("initial_prompt")
            assert prompt is None

    def test_vocabulary_prepended_to_prompt(self) -> None:
        from app.adapters.stt.config import WhisperConfig
        from app.adapters.stt.faster_whisper_engine import FasterWhisperEngine

        cfg = WhisperConfig(vocabulary=["Битрикс", "КП"], initial_prompt=None)
        engine = FasterWhisperEngine(cfg)

        with patch.object(engine, "_load_model") as mock_load:
            mock_model = MagicMock()
            mock_info = MagicMock()
            mock_info.language = "ru"
            mock_model.transcribe.return_value = (iter([]), mock_info)
            mock_load.return_value = mock_model

            engine.transcribe(_make_payload())

            call_kwargs = mock_model.transcribe.call_args
            prompt = call_kwargs.kwargs.get("initial_prompt")
            assert prompt is not None
            assert "Битрикс" in prompt
            assert "КП" in prompt

    def test_vocabulary_and_prompt_combined(self) -> None:
        from app.adapters.stt.config import WhisperConfig
        from app.adapters.stt.faster_whisper_engine import FasterWhisperEngine

        cfg = WhisperConfig(vocabulary=["CRM"], initial_prompt="Говорит менеджер")
        engine = FasterWhisperEngine(cfg)

        with patch.object(engine, "_load_model") as mock_load:
            mock_model = MagicMock()
            mock_info = MagicMock()
            mock_info.language = "ru"
            mock_model.transcribe.return_value = (iter([]), mock_info)
            mock_load.return_value = mock_model

            engine.transcribe(_make_payload())

            call_kwargs = mock_model.transcribe.call_args
            prompt = call_kwargs.kwargs.get("initial_prompt")
            assert prompt is not None
            assert "CRM" in prompt
            assert "Говорит менеджер" in prompt

    def test_changing_vocabulary_no_code_change(self) -> None:
        """Config alone controls prompt — no code modification needed."""
        from app.adapters.stt.config import WhisperConfig
        from app.adapters.stt.faster_whisper_engine import FasterWhisperEngine

        cfg1 = WhisperConfig(vocabulary=["Продукт Первый"])
        cfg2 = WhisperConfig(vocabulary=["Продукт Второй", "Продукт Третий"])

        engine1 = FasterWhisperEngine(cfg1)
        engine2 = FasterWhisperEngine(cfg2)

        assert "Продукт Первый" in (engine1._build_initial_prompt() or "")
        assert "Продукт Второй" in (engine2._build_initial_prompt() or "")
        assert "Продукт Третий" in (engine2._build_initial_prompt() or "")
