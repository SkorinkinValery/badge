"""M9-T4: Contract tests for RU-cloud LLM analyzers (YandexGPT, GigaChat).

API calls are mocked — no real credentials required.
Both adapters must satisfy the same Analyzer contract as OpenAICompatibleAnalyzer.
"""

from __future__ import annotations

import json
import uuid
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.config.kpi import load_kpi_config
from app.core.domain import Segment, Transcript
from app.core.ports import AnalysisResult, Analyzer
from tests.contract.helpers import assert_valid_analysis_result

_SAMPLE_TRANSCRIPT = Transcript(
    id=uuid.uuid4(),
    recording_id=uuid.uuid4(),
    full_text="Добрый день, чем могу помочь?",
    segments=(
        Segment(start=0.0, end=2.5, text="Добрый день,"),
        Segment(start=2.5, end=4.0, text="чем могу помочь?"),
    ),
    detected_language="ru",
)


def _make_kpi_json() -> str:
    kpi_cfg = load_kpi_config()
    payload: dict[str, Any] = {}
    for kpi in kpi_cfg.kpis:
        payload[kpi.id] = {"value": 7.0, "quote": "тест", "comment": "ok"}
    return json.dumps(payload)


# ---------------------------------------------------------------------------
# YandexGptAnalyzer
# ---------------------------------------------------------------------------


def _yandex_gpt_ok_response(content: str) -> MagicMock:
    """Mock httpx.Response for YandexGPT completion."""
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {
        "result": {
            "alternatives": [
                {
                    "message": {"role": "assistant", "text": content},
                    "status": "ALTERNATIVE_STATUS_FINAL",
                }
            ],
            "usage": {"inputTextTokens": 100, "completionTokens": 200, "totalTokens": 300},
            "modelVersion": "23.10.2024",
        }
    }
    return resp


@pytest.fixture
def yandex_gpt_analyzer() -> Analyzer:
    from app.adapters.analyzer.yandexgpt import YandexGptAnalyzer

    return YandexGptAnalyzer(api_key="test-iam-key", folder_id="test-folder")


class TestYandexGptAnalyzerContract:
    """YandexGptAnalyzer must satisfy the Analyzer contract."""

    def test_impl_satisfies_protocol(self, yandex_gpt_analyzer: Analyzer) -> None:
        assert isinstance(yandex_gpt_analyzer, Analyzer)

    def test_analyze_returns_analysis_result(self, yandex_gpt_analyzer: Analyzer) -> None:
        kpi_json = _make_kpi_json()
        with patch("httpx.post", return_value=_yandex_gpt_ok_response(kpi_json)):
            result = yandex_gpt_analyzer.analyze(_SAMPLE_TRANSCRIPT)
        assert isinstance(result, AnalysisResult)

    def test_analysis_has_non_empty_summary(self, yandex_gpt_analyzer: Analyzer) -> None:
        kpi_json = _make_kpi_json()
        with patch("httpx.post", return_value=_yandex_gpt_ok_response(kpi_json)):
            result = yandex_gpt_analyzer.analyze(_SAMPLE_TRANSCRIPT)
        assert result.summary

    def test_kpi_json_validates_against_schema(self, yandex_gpt_analyzer: Analyzer) -> None:
        kpi_json = _make_kpi_json()
        with patch("httpx.post", return_value=_yandex_gpt_ok_response(kpi_json)):
            result = yandex_gpt_analyzer.analyze(_SAMPLE_TRANSCRIPT)
        kpi_cfg = load_kpi_config()
        assert_valid_analysis_result(result, {kpi.id for kpi in kpi_cfg.kpis})

    def test_creds_not_hardcoded(self, yandex_gpt_analyzer: Analyzer) -> None:
        import inspect

        from app.adapters.analyzer.yandexgpt import YandexGptAnalyzer

        source = inspect.getsource(YandexGptAnalyzer)
        assert "test-iam-key" not in source
        assert "test-folder" not in source

    def test_api_error_raises(self, yandex_gpt_analyzer: Analyzer) -> None:
        import httpx

        err_resp = MagicMock()
        err_resp.status_code = 401
        err_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized", request=MagicMock(), response=err_resp
        )
        with patch("httpx.post", return_value=err_resp), pytest.raises(httpx.HTTPStatusError):
            yandex_gpt_analyzer.analyze(_SAMPLE_TRANSCRIPT)

    def test_invalid_json_raises_value_error(self, yandex_gpt_analyzer: Analyzer) -> None:
        with patch("httpx.post", return_value=_yandex_gpt_ok_response("not json {")), pytest.raises((ValueError, Exception)):
            yandex_gpt_analyzer.analyze(_SAMPLE_TRANSCRIPT)


# ---------------------------------------------------------------------------
# GigaChatAnalyzer
# ---------------------------------------------------------------------------


def _gigachat_ok_response(content: str) -> MagicMock:
    """Mock httpx.Response for GigaChat OpenAI-compatible completion."""
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {
        "choices": [
            {
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
                "index": 0,
            }
        ],
        "created": 1700000000,
        "model": "GigaChat:latest",
        "object": "chat.completion",
        "usage": {"prompt_tokens": 100, "completion_tokens": 200, "total_tokens": 300},
    }
    return resp


@pytest.fixture
def gigachat_analyzer() -> Analyzer:
    from app.adapters.analyzer.gigachat import GigaChatAnalyzer

    return GigaChatAnalyzer(auth_token="test-token", scope="GIGACHAT_API_PERS")


class TestGigaChatAnalyzerContract:
    """GigaChatAnalyzer must satisfy the Analyzer contract."""

    def test_impl_satisfies_protocol(self, gigachat_analyzer: Analyzer) -> None:
        assert isinstance(gigachat_analyzer, Analyzer)

    def test_analyze_returns_analysis_result(self, gigachat_analyzer: Analyzer) -> None:
        kpi_json = _make_kpi_json()
        with patch("httpx.post", return_value=_gigachat_ok_response(kpi_json)):
            result = gigachat_analyzer.analyze(_SAMPLE_TRANSCRIPT)
        assert isinstance(result, AnalysisResult)

    def test_analysis_has_non_empty_summary(self, gigachat_analyzer: Analyzer) -> None:
        kpi_json = _make_kpi_json()
        with patch("httpx.post", return_value=_gigachat_ok_response(kpi_json)):
            result = gigachat_analyzer.analyze(_SAMPLE_TRANSCRIPT)
        assert result.summary

    def test_kpi_json_validates_against_schema(self, gigachat_analyzer: Analyzer) -> None:
        kpi_json = _make_kpi_json()
        with patch("httpx.post", return_value=_gigachat_ok_response(kpi_json)):
            result = gigachat_analyzer.analyze(_SAMPLE_TRANSCRIPT)
        kpi_cfg = load_kpi_config()
        assert_valid_analysis_result(result, {kpi.id for kpi in kpi_cfg.kpis})

    def test_creds_not_hardcoded(self, gigachat_analyzer: Analyzer) -> None:
        import inspect

        from app.adapters.analyzer.gigachat import GigaChatAnalyzer

        source = inspect.getsource(GigaChatAnalyzer)
        assert "test-token" not in source

    def test_api_error_raises(self, gigachat_analyzer: Analyzer) -> None:
        import httpx

        err_resp = MagicMock()
        err_resp.status_code = 403
        err_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "403 Forbidden", request=MagicMock(), response=err_resp
        )
        with patch("httpx.post", return_value=err_resp), pytest.raises(httpx.HTTPStatusError):
            gigachat_analyzer.analyze(_SAMPLE_TRANSCRIPT)

    def test_invalid_json_raises(self, gigachat_analyzer: Analyzer) -> None:
        with patch("httpx.post", return_value=_gigachat_ok_response("bad json {")), pytest.raises((ValueError, Exception)):
            gigachat_analyzer.analyze(_SAMPLE_TRANSCRIPT)
