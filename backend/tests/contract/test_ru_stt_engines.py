"""M9-T3: Contract tests for RU-cloud STT engines (YandexStt, SberStt).

API calls are mocked — no real credentials required.
Both adapters must satisfy the same STTEngine contract as FasterWhisperEngine.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from app.core.ports import AudioPayload, STTEngine
from tests.contract.helpers import assert_valid_transcript

_SAMPLE_PAYLOAD = AudioPayload(
    audio_data=b"\x00" * 3200,
    sample_rate=16000,
    manager_id=uuid.uuid4(),
    channel="file",
    started_at=datetime.now(tz=UTC),
    consent_flag=True,
)


# ---------------------------------------------------------------------------
# YandexSttEngine
# ---------------------------------------------------------------------------


def _yandex_ok_response() -> MagicMock:
    """Mock httpx.Response for Yandex SpeechKit synchronous STT."""
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {
        "result": "Добрый день, чем могу помочь?",
        "chunks": [
            {
                "alternatives": [
                    {
                        "words": [
                            {"startTime": "0s", "endTime": "1.5s", "word": "Добрый"},
                            {"startTime": "1.5s", "endTime": "2.0s", "word": "день"},
                        ],
                        "text": "Добрый день, чем могу помочь?",
                        "confidence": 1.0,
                    }
                ],
                "channelTag": "1",
                "final": True,
                "finalIntervalBeginMs": 0,
                "finalIntervalEndMs": 4000,
            }
        ],
        "languageCode": "ru-RU",
    }
    return resp


@pytest.fixture
def yandex_engine() -> STTEngine:
    from app.adapters.stt.yandex_stt import YandexSttEngine

    return YandexSttEngine(api_key="test-api-key", folder_id="test-folder")


class TestYandexSttEngineContract:
    """YandexSttEngine must satisfy the STTEngine contract."""

    def test_impl_satisfies_protocol(self, yandex_engine: STTEngine) -> None:
        assert isinstance(yandex_engine, STTEngine)

    def test_transcribe_returns_transcript(self, yandex_engine: STTEngine) -> None:
        from app.core.domain import Transcript

        with patch("httpx.post", return_value=_yandex_ok_response()):
            result = yandex_engine.transcribe(_SAMPLE_PAYLOAD)
        assert isinstance(result, Transcript)

    def test_transcript_has_non_empty_segments(self, yandex_engine: STTEngine) -> None:
        with patch("httpx.post", return_value=_yandex_ok_response()):
            result = yandex_engine.transcribe(_SAMPLE_PAYLOAD)
        assert result.segments

    def test_transcript_has_detected_language(self, yandex_engine: STTEngine) -> None:
        with patch("httpx.post", return_value=_yandex_ok_response()):
            result = yandex_engine.transcribe(_SAMPLE_PAYLOAD)
        assert result.detected_language

    def test_transcript_timecodes_monotone(self, yandex_engine: STTEngine) -> None:
        with patch("httpx.post", return_value=_yandex_ok_response()):
            result = yandex_engine.transcribe(_SAMPLE_PAYLOAD)
        assert_valid_transcript(result)

    def test_creds_from_config_not_hardcoded(self, yandex_engine: STTEngine) -> None:
        """Credentials must come from constructor, not hardcoded in adapter."""
        import inspect

        from app.adapters.stt.yandex_stt import YandexSttEngine

        source = inspect.getsource(YandexSttEngine)
        assert "test-api-key" not in source
        assert "test-folder" not in source

    def test_api_error_raises(self, yandex_engine: STTEngine) -> None:
        """HTTP error from Yandex API must propagate, not silently return empty."""
        import httpx

        err_resp = MagicMock()
        err_resp.status_code = 403
        err_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "403 Forbidden", request=MagicMock(), response=err_resp
        )
        with patch("httpx.post", return_value=err_resp), pytest.raises(httpx.HTTPStatusError):
            yandex_engine.transcribe(_SAMPLE_PAYLOAD)


# ---------------------------------------------------------------------------
# SberSttEngine
# ---------------------------------------------------------------------------


def _sber_ok_response() -> MagicMock:
    """Mock httpx.Response for Sber SaluteSpeech STT."""
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {
        "status": 200,
        "result": [
            {
                "results": [
                    {
                        "transcript": "Добрый день, чем могу помочь?",
                        "confidence": 0.99,
                        "words": [
                            {"start_ms": 0, "end_ms": 800, "word": "Добрый"},
                            {"start_ms": 800, "end_ms": 1200, "word": "день"},
                        ],
                    }
                ],
                "channel": 0,
                "eou": True,
            }
        ],
        "language": "ru",
    }
    return resp


@pytest.fixture
def sber_engine() -> STTEngine:
    from app.adapters.stt.sber_stt import SberSttEngine

    return SberSttEngine(auth_token="test-token")


class TestSberSttEngineContract:
    """SberSttEngine must satisfy the STTEngine contract."""

    def test_impl_satisfies_protocol(self, sber_engine: STTEngine) -> None:
        assert isinstance(sber_engine, STTEngine)

    def test_transcribe_returns_transcript(self, sber_engine: STTEngine) -> None:
        from app.core.domain import Transcript

        with patch("httpx.post", return_value=_sber_ok_response()):
            result = sber_engine.transcribe(_SAMPLE_PAYLOAD)
        assert isinstance(result, Transcript)

    def test_transcript_has_non_empty_segments(self, sber_engine: STTEngine) -> None:
        with patch("httpx.post", return_value=_sber_ok_response()):
            result = sber_engine.transcribe(_SAMPLE_PAYLOAD)
        assert result.segments

    def test_transcript_has_detected_language(self, sber_engine: STTEngine) -> None:
        with patch("httpx.post", return_value=_sber_ok_response()):
            result = sber_engine.transcribe(_SAMPLE_PAYLOAD)
        assert result.detected_language

    def test_transcript_timecodes_monotone(self, sber_engine: STTEngine) -> None:
        with patch("httpx.post", return_value=_sber_ok_response()):
            result = sber_engine.transcribe(_SAMPLE_PAYLOAD)
        assert_valid_transcript(result)

    def test_creds_from_config_not_hardcoded(self, sber_engine: STTEngine) -> None:
        import inspect

        from app.adapters.stt.sber_stt import SberSttEngine

        source = inspect.getsource(SberSttEngine)
        assert "test-token" not in source

    def test_api_error_raises(self, sber_engine: STTEngine) -> None:
        import httpx

        err_resp = MagicMock()
        err_resp.status_code = 401
        err_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized", request=MagicMock(), response=err_resp
        )
        with patch("httpx.post", return_value=err_resp), pytest.raises(httpx.HTTPStatusError):
            sber_engine.transcribe(_SAMPLE_PAYLOAD)
