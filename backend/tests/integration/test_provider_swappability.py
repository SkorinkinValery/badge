"""M9-T5: Provider swappability invariant test.

Proves that the same pipeline graph produces a valid analysis
when given different provider combinations (stub / cloud / vLLM / RU-cloud)
via config-only switching — core pipeline code is never modified.
"""

from __future__ import annotations

import json
import uuid
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from langgraph.checkpoint.memory import MemorySaver

from app.adapters.analyzer.stub_analyzer import StubAnalyzer
from app.adapters.stt.stub_stt import StubSTTEngine
from app.config.kpi import load_kpi_config
from app.config.settings import LLMProviderConfig
from app.core.domain.enums import RecordingStatus
from app.core.pipeline.nodes import make_nodes
from app.core.pipeline.state import PipelineState
from app.core.ports import Analyzer, STTEngine

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_kpi_json() -> str:
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


def _mock_httpx_response(content: str) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    return resp


def _initial_state(recording_id: uuid.UUID) -> PipelineState:
    return {  # type: ignore[return-value]
        "recording_id": str(recording_id),
        "status": RecordingStatus.QUEUED.value,
        "audio_payload": None,
        "transcript": None,
        "analysis_result": None,
        "score": None,
        "verdict": None,
        "export_result": None,
        "crm_config": {"active_crm": "json", "crm": {}},
        "stage_error": None,
        "retry": 0,
    }


def _run_graph(stt: STTEngine, analyzer: Analyzer) -> PipelineState:
    """Run the pipeline with injected STT + Analyzer via make_nodes."""
    from langgraph.graph import END, StateGraph

    recording_id = uuid.uuid4()
    nodes = make_nodes(stt_engine=stt, analyzer=analyzer)
    saver = MemorySaver()

    builder: StateGraph = StateGraph(PipelineState)
    for name, fn in nodes.items():
        builder.add_node(name, fn)

    builder.set_entry_point("normalizing")
    builder.add_edge("normalizing", "transcribing")
    builder.add_edge("transcribing", "analyzing")
    builder.add_edge("analyzing", "scoring")
    builder.add_edge("scoring", "exporting")
    builder.add_edge("exporting", END)

    graph = builder.compile(checkpointer=saver)

    thread_id = str(recording_id)
    config = {"configurable": {"thread_id": thread_id}}
    final = graph.invoke(_initial_state(recording_id), config=config)
    return final  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Provider configurations as fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def stub_providers() -> tuple[STTEngine, Analyzer]:
    """All-stub: fastest, no external calls."""
    return StubSTTEngine(), StubAnalyzer()


@pytest.fixture
def cloud_providers() -> tuple[STTEngine, Analyzer]:
    """Stub STT + OpenAI-compatible (cloud) Analyzer (mocked HTTP)."""
    from app.adapters.analyzer.openai_compatible import OpenAICompatibleAnalyzer

    config = LLMProviderConfig(
        base_url="https://api.openai.com/v1",
        model="gpt-4o-mini",
        api_key="test-key",
        structured_output_mode="json_object",
    )
    return StubSTTEngine(), OpenAICompatibleAnalyzer(config)


@pytest.fixture
def vllm_providers() -> tuple[STTEngine, Analyzer]:
    """Stub STT + OpenAICompatibleAnalyzer pointing at vLLM (mocked)."""
    from app.adapters.analyzer.openai_compatible import OpenAICompatibleAnalyzer

    config = LLMProviderConfig(
        base_url="http://vllm:8000/v1",
        model="Qwen/Qwen2.5-7B-Instruct-AWQ",
        api_key="no-key",
        structured_output_mode="guided_json",
    )
    return StubSTTEngine(), OpenAICompatibleAnalyzer(config)


@pytest.fixture
def ru_cloud_providers() -> tuple[STTEngine, Analyzer]:
    """YandexStt + YandexGPT (both mocked)."""
    from app.adapters.analyzer.yandexgpt import YandexGptAnalyzer
    from app.adapters.stt.yandex_stt import YandexSttEngine

    return (
        YandexSttEngine(api_key="test-key", folder_id="test-folder"),
        YandexGptAnalyzer(api_key="test-key", folder_id="test-folder"),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_stub_providers_complete_pipeline(stub_providers: tuple[STTEngine, Analyzer]) -> None:
    """All-stub config: pipeline must complete without any external calls."""
    stt, analyzer = stub_providers
    final = _run_graph(stt, analyzer)
    assert final.get("analysis_result") is not None, "analysis_result must be set after pipeline completes"
    assert final.get("status") != RecordingStatus.FAILED.value


def test_cloud_providers_complete_pipeline(cloud_providers: tuple[STTEngine, Analyzer]) -> None:
    """Cloud config: mocked OpenAI response must produce valid analysis."""
    stt, analyzer = cloud_providers
    kpi_json = _make_kpi_json()
    from app.adapters.analyzer.openai_compatible import OpenAICompatibleAnalyzer
    assert isinstance(analyzer, OpenAICompatibleAnalyzer)
    with patch.object(analyzer._client.chat.completions, "create", return_value=_mock_openai_response(kpi_json)):
        final = _run_graph(stt, analyzer)
    assert final.get("analysis_result") is not None
    assert final.get("status") != RecordingStatus.FAILED.value


def test_vllm_providers_complete_pipeline(vllm_providers: tuple[STTEngine, Analyzer]) -> None:
    """vLLM config: guided_json mode must produce same valid analysis."""
    stt, analyzer = vllm_providers
    kpi_json = _make_kpi_json()
    from app.adapters.analyzer.openai_compatible import OpenAICompatibleAnalyzer
    assert isinstance(analyzer, OpenAICompatibleAnalyzer)
    with patch.object(analyzer._client.chat.completions, "create", return_value=_mock_openai_response(kpi_json)):
        final = _run_graph(stt, analyzer)
    assert final.get("analysis_result") is not None
    assert final.get("status") != RecordingStatus.FAILED.value


def test_ru_cloud_providers_complete_pipeline(ru_cloud_providers: tuple[STTEngine, Analyzer]) -> None:
    """RU-cloud config: mocked Yandex APIs must produce valid analysis."""
    stt, analyzer = ru_cloud_providers

    yandex_stt_resp = MagicMock()
    yandex_stt_resp.raise_for_status = MagicMock()
    yandex_stt_resp.json.return_value = {
        "result": "Добрый день",
        "chunks": [
            {
                "alternatives": [
                    {
                        "words": [{"startTime": "0s", "endTime": "1s", "word": "Добрый"}],
                        "text": "Добрый день",
                        "confidence": 1.0,
                    }
                ],
                "channelTag": "1",
                "final": True,
                "finalIntervalBeginMs": 0,
                "finalIntervalEndMs": 1000,
            }
        ],
        "languageCode": "ru-RU",
    }

    yandex_gpt_resp = MagicMock()
    yandex_gpt_resp.raise_for_status = MagicMock()
    yandex_gpt_resp.json.return_value = {
        "result": {
            "alternatives": [
                {"message": {"role": "assistant", "text": _make_kpi_json()}, "status": "FINAL"}
            ],
            "usage": {},
            "modelVersion": "1.0",
        }
    }

    call_count = 0

    def _httpx_post_router(*args: Any, **kwargs: Any) -> MagicMock:
        nonlocal call_count
        call_count += 1
        url = args[0] if args else kwargs.get("url", "")
        if "stt" in str(url):
            return yandex_stt_resp
        return yandex_gpt_resp

    with patch("httpx.post", side_effect=_httpx_post_router):
        final = _run_graph(stt, analyzer)

    assert final.get("analysis_result") is not None
    assert final.get("status") != RecordingStatus.FAILED.value


def test_core_pipeline_code_has_no_adapter_imports() -> None:
    """Ports & adapters invariant: core pipeline must not import concrete adapters."""
    import importlib
    import pkgutil

    import app.core.pipeline as pipeline_pkg

    forbidden_prefixes = (
        "app.adapters.",
        "openai",
        "httpx",
        "faster_whisper",
        "gspread",
    )

    for mod_info in pkgutil.walk_packages(
        path=pipeline_pkg.__path__,
        prefix=pipeline_pkg.__name__ + ".",
    ):
        mod = importlib.import_module(mod_info.name)
        for attr in dir(mod):
            obj = getattr(mod, attr, None)
            if obj is None:
                continue
            module_name = getattr(obj, "__module__", "") or ""
            for prefix in forbidden_prefixes:
                assert not module_name.startswith(prefix), (
                    f"core.pipeline.{mod_info.name} imports {module_name} — "
                    f"violates ports & adapters invariant"
                )


def test_provider_switch_is_config_only() -> None:
    """Switching providers must only change config data, not code paths."""
    from app.adapters.analyzer.openai_compatible import OpenAICompatibleAnalyzer

    cloud_cfg = LLMProviderConfig(base_url="https://api.openai.com/v1", model="gpt-4o-mini")
    vllm_cfg = LLMProviderConfig(
        base_url="http://vllm:8000/v1",
        model="Qwen/Qwen2.5-7B-Instruct-AWQ",
        structured_output_mode="guided_json",
    )

    cloud_analyzer = OpenAICompatibleAnalyzer(cloud_cfg)
    vllm_analyzer = OpenAICompatibleAnalyzer(vllm_cfg)

    # Both are same class — no branching, only config data differs
    assert type(cloud_analyzer) is type(vllm_analyzer)
    assert cloud_analyzer._config.base_url != vllm_analyzer._config.base_url
    assert cloud_analyzer._config.structured_output_mode == "json_object"
    assert vllm_analyzer._config.structured_output_mode == "guided_json"
