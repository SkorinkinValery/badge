"""M9-T2: OpenAICompatibleAnalyzer with guided_json for vLLM.

Verifies that the same adapter works against cloud (json_object response_format)
and vLLM (guided_json via extra_body) without branching on provider in core code.
"""

from __future__ import annotations

import json
import uuid
from typing import Any
from unittest.mock import MagicMock, patch

from app.adapters.analyzer.openai_compatible import OpenAICompatibleAnalyzer
from app.adapters.analyzer.schema import build_kpi_result_model
from app.config.kpi import load_kpi_config
from app.config.settings import LLMProviderConfig
from app.core.domain.transcript import Segment, Transcript


def _make_transcript() -> Transcript:
    return Transcript(
        id=uuid.uuid4(),
        recording_id=uuid.uuid4(),
        segments=[Segment(start=0.0, end=5.0, text="Добрый день, чем помочь?", speaker=None)],
        language="ru",
        full_text="Добрый день, чем помочь?",
        detected_language="ru",
    )


def _make_kpi_response() -> str:
    """Build a minimal valid KPI JSON matching the schema from kpi.yaml."""
    kpi_cfg = load_kpi_config()
    payload: dict[str, Any] = {}
    for kpi in kpi_cfg.kpis:
        payload[kpi.id] = {"value": 7.0, "quote": "тест", "comment": "ok"}
    return json.dumps(payload)


def _mock_openai_response(content: str) -> MagicMock:
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


# --- Tests ---


def test_cloud_mode_uses_json_object_response_format() -> None:
    """Cloud (OpenAI) mode: response_format=json_object, no extra_body."""
    config = LLMProviderConfig(
        adapter="openai_compatible",
        base_url="https://api.openai.com/v1",
        model="gpt-4o-mini",
        api_key="test-key",
        structured_output_mode="json_object",
    )
    analyzer = OpenAICompatibleAnalyzer(config)
    transcript = _make_transcript()

    with patch.object(analyzer._client.chat.completions, "create", return_value=_mock_openai_response(_make_kpi_response())) as mock_create:
        analyzer.analyze(transcript)

    call_kwargs = mock_create.call_args.kwargs
    assert call_kwargs.get("response_format") == {"type": "json_object"}
    assert "extra_body" not in call_kwargs or not call_kwargs.get("extra_body")


def test_vllm_mode_uses_guided_json() -> None:
    """vLLM mode: guided_json via extra_body with KpiResult JSON schema."""
    config = LLMProviderConfig(
        adapter="openai_compatible",
        base_url="http://vllm:8000/v1",
        model="Qwen/Qwen2.5-7B-Instruct-AWQ",
        api_key="no-key",
        structured_output_mode="guided_json",
    )
    analyzer = OpenAICompatibleAnalyzer(config)
    transcript = _make_transcript()

    with patch.object(analyzer._client.chat.completions, "create", return_value=_mock_openai_response(_make_kpi_response())) as mock_create:
        analyzer.analyze(transcript)

    call_kwargs = mock_create.call_args.kwargs
    extra_body = call_kwargs.get("extra_body") or {}
    assert "guided_json" in extra_body, "vLLM mode must pass guided_json in extra_body"
    schema = extra_body["guided_json"]
    assert isinstance(schema, dict)
    assert "properties" in schema or "$defs" in schema, "guided_json must be a valid JSON schema"


def test_guided_json_schema_matches_kpi_result_model() -> None:
    """guided_json schema must be the exported KpiResult JSON schema."""
    config = LLMProviderConfig(
        adapter="openai_compatible",
        base_url="http://vllm:8000/v1",
        model="Qwen/Qwen2.5-7B-Instruct-AWQ",
        api_key="no-key",
        structured_output_mode="guided_json",
    )
    analyzer = OpenAICompatibleAnalyzer(config)
    transcript = _make_transcript()

    with patch.object(analyzer._client.chat.completions, "create", return_value=_mock_openai_response(_make_kpi_response())) as mock_create:
        analyzer.analyze(transcript)

    call_kwargs = mock_create.call_args.kwargs
    extra_body = call_kwargs.get("extra_body") or {}
    schema = extra_body["guided_json"]

    kpi_cfg = load_kpi_config()
    kpi_model = build_kpi_result_model(kpi_cfg)
    expected_schema = kpi_model.model_json_schema()
    assert schema == expected_schema


def test_no_provider_branching_in_adapter() -> None:
    """Adapter code must not branch on provider name — only structured_output_mode matters."""
    import inspect

    import app.adapters.analyzer.openai_compatible as mod

    source = inspect.getsource(mod)
    # Ensure no hardcoded cloud/vllm names in branching logic
    assert "openai.com" not in source, "base_url must not be hardcoded in adapter source"
    assert "vllm" not in source.lower() or source.lower().count("vllm") <= 2, (
        "adapter should not have deep vllm-specific branching"
    )


def test_result_validates_same_schema_regardless_of_mode() -> None:
    """Both modes must produce AnalysisResult with same KPI schema."""
    kpi_response = _make_kpi_response()

    for mode in ("json_object", "guided_json"):
        config = LLMProviderConfig(
            adapter="openai_compatible",
            base_url="http://localhost:8000/v1",
            model="test-model",
            api_key="test-key",
            structured_output_mode=mode,
        )
        analyzer = OpenAICompatibleAnalyzer(config)
        transcript = _make_transcript()

        with patch.object(analyzer._client.chat.completions, "create", return_value=_mock_openai_response(kpi_response)):
            result = analyzer.analyze(transcript)

        assert result.summary
        kpi_cfg = load_kpi_config()
        for kpi in kpi_cfg.kpis:
            assert kpi.id in result.kpi_json, f"KPI {kpi.id} missing in mode={mode}"
