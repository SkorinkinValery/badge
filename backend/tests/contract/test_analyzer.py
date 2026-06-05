"""Contract tests for Analyzer port — M1-T3 / M4-T3."""

from __future__ import annotations

import json
import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.config.kpi import load_kpi_config
from app.core.domain import Segment, Transcript
from app.core.ports import AnalysisResult, Analyzer
from tests.contract.helpers import assert_valid_analysis_result


def get_analyzer_impls() -> list[tuple[str, Analyzer]]:
    impls: list[tuple[str, Analyzer]] = []
    try:
        from app.adapters.analyzer.stub_analyzer import StubAnalyzer
        impls.append(("StubAnalyzer", StubAnalyzer()))
    except ImportError:
        pass
    return impls


_impls = get_analyzer_impls()
_ids = [label for label, _ in _impls]

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


@pytest.mark.contract
@pytest.mark.skipif(not _impls, reason="No Analyzer implementations registered yet")
@pytest.mark.parametrize("impl", [impl for _, impl in _impls], ids=_ids)
class TestAnalyzerContract:
    def test_analyze_returns_analysis_result(self, impl: Analyzer) -> None:
        result = impl.analyze(_SAMPLE_TRANSCRIPT)
        assert isinstance(result, AnalysisResult)

    def test_analysis_has_non_empty_summary(self, impl: Analyzer) -> None:
        result = impl.analyze(_SAMPLE_TRANSCRIPT)
        assert result.summary

    def test_kpi_keys_subset_of_configured_kpis(self, impl: Analyzer) -> None:
        cfg = load_kpi_config()
        kpi_ids = {k.id for k in cfg.kpis}
        result = impl.analyze(_SAMPLE_TRANSCRIPT)
        assert_valid_analysis_result(result, kpi_ids)

    def test_analyze_with_script_returns_analysis(self, impl: Analyzer) -> None:
        result = impl.analyze(_SAMPLE_TRANSCRIPT, script="Этап 1: Приветствие")
        assert isinstance(result, AnalysisResult)

    def test_impl_satisfies_protocol(self, impl: Analyzer) -> None:
        assert isinstance(impl, Analyzer)


def _make_mock_llm_response(cfg_kpis: list[object]) -> str:
    """Build a fake LLM JSON response matching KpiResult schema."""
    from app.config.kpi import KpiItem

    kpis = [k for k in cfg_kpis if isinstance(k, KpiItem)]
    entries = {}
    for kpi in kpis:
        entries[kpi.id] = {
            "kpi_type": kpi.type,
            "value": 0.0 if kpi.type == "fact" else 7.0,
            "quote": "Добрый день",
            "comment": "ok",
        }
    return json.dumps(entries)


@pytest.mark.contract
class TestOpenAICompatibleAnalyzerContract:
    """Contract tests with mocked HTTP (no real API key required in CI)."""

    @pytest.fixture
    def analyzer(self) -> Analyzer:
        try:
            from app.adapters.analyzer.openai_compatible import OpenAICompatibleAnalyzer
            from app.config.settings import load_providers_config

            cfg = load_providers_config()
            return OpenAICompatibleAnalyzer(cfg.active_llm)
        except ImportError as e:
            pytest.skip(f"OpenAICompatibleAnalyzer not available: {e}")

    def _patch_call(self, analyzer: object, kpis: list[object]) -> MagicMock:
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = _make_mock_llm_response(kpis)
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_resp

        patcher = patch.object(analyzer, "_client", mock_client)  # type: ignore[arg-type]
        patcher.start()
        return mock_client

    def test_analyze_returns_analysis_result(self, analyzer: Analyzer) -> None:
        cfg = load_kpi_config()
        self._patch_call(analyzer, cfg.kpis)
        result = analyzer.analyze(_SAMPLE_TRANSCRIPT)
        assert isinstance(result, AnalysisResult)

    def test_analysis_has_summary(self, analyzer: Analyzer) -> None:
        cfg = load_kpi_config()
        self._patch_call(analyzer, cfg.kpis)
        result = analyzer.analyze(_SAMPLE_TRANSCRIPT)
        assert result.summary

    def test_kpi_json_has_valid_keys(self, analyzer: Analyzer) -> None:
        cfg = load_kpi_config()
        self._patch_call(analyzer, cfg.kpis)
        kpi_ids = {k.id for k in cfg.kpis}
        result = analyzer.analyze(_SAMPLE_TRANSCRIPT)
        for key in result.kpi_json:
            assert key in kpi_ids

    def test_impl_satisfies_protocol(self, analyzer: Analyzer) -> None:
        assert isinstance(analyzer, Analyzer)

    def test_base_url_and_model_from_config(self, analyzer: Analyzer) -> None:
        """Adapter reads base_url/model from config, not hardcoded."""
        from app.adapters.analyzer.openai_compatible import OpenAICompatibleAnalyzer

        assert isinstance(analyzer, OpenAICompatibleAnalyzer)
        assert analyzer._config.base_url
        assert analyzer._config.model
