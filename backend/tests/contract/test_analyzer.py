"""Contract tests for Analyzer port — M1-T3."""

from __future__ import annotations

import uuid

import pytest

from app.config.kpi import load_kpi_config
from app.core.domain import Segment, Transcript
from app.core.ports import AnalysisResult, Analyzer
from tests.contract.helpers import assert_valid_analysis_result


def get_analyzer_impls() -> list[tuple[str, Analyzer]]:
    try:
        from app.adapters.analyzer.stub_analyzer import StubAnalyzer
        return [("StubAnalyzer", StubAnalyzer())]
    except ImportError:
        return []


_impls = get_analyzer_impls()
_ids = [label for label, _ in _impls]

_SAMPLE_TRANSCRIPT = Transcript(
    id=uuid.uuid4(),
    recording_id=uuid.uuid4(),
    full_text="Добрый день, чем могу помочь?",
    segments=[
        Segment(start=0.0, end=2.5, text="Добрый день,"),
        Segment(start=2.5, end=4.0, text="чем могу помочь?"),
    ],
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
