"""Shared assertion helpers for contract tests."""

from __future__ import annotations

from app.core.domain import Transcript
from app.core.ports import AnalysisResult, ExportResult


def assert_valid_transcript(t: Transcript) -> None:
    assert t.segments, "Transcript must have at least one segment"
    assert t.detected_language, "detected_language must not be empty"
    prev_end = -1.0
    for seg in t.segments:
        assert seg.start >= 0, "segment start must be non-negative"
        assert seg.end > seg.start, "segment end must be > start"
        assert seg.end >= prev_end, "segment timecodes must be monotone"
        prev_end = seg.end


def assert_valid_analysis_result(result: AnalysisResult, kpi_ids: set[str]) -> None:
    assert result.summary, "summary must not be empty"
    assert result.kpi_json, "kpi_json must not be empty"
    for key in result.kpi_json:
        assert key in kpi_ids, f"kpi key '{key}' not in configured KPI ids"


def assert_valid_export_result(result: ExportResult) -> None:
    assert isinstance(result.success, bool)
    if result.success:
        assert result.error is None
