"""M10-T4: regression_harness.py tests.

Verifies that the harness compares current metrics vs baseline,
emits warnings on regression, and is non-blocking (returns 0 even on drift).
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest


def _write_baseline(path: Path, wer: float, kpi_mae: dict[str, float]) -> None:
    path.write_text(json.dumps({"wer": wer, "kpi_mae": kpi_mae}))


def test_no_regression_when_metrics_improve() -> None:
    from scripts.regression_harness import compare_metrics

    baseline = {"wer": 0.20, "kpi_mae": {"greeting": 2.0}}
    current = {"wer": 0.15, "kpi_mae": {"greeting": 1.5}}
    result = compare_metrics(current=current, baseline=baseline)
    assert not result.has_regression


def test_regression_detected_on_wer_increase() -> None:
    from scripts.regression_harness import compare_metrics

    baseline = {"wer": 0.10, "kpi_mae": {"greeting": 1.0}}
    current = {"wer": 0.20, "kpi_mae": {"greeting": 1.0}}  # WER doubled
    result = compare_metrics(current=current, baseline=baseline)
    assert result.has_regression
    assert "wer" in result.regressions


def test_regression_detected_on_kpi_mae_increase() -> None:
    from scripts.regression_harness import compare_metrics

    baseline = {"wer": 0.10, "kpi_mae": {"greeting": 1.0}}
    current = {"wer": 0.10, "kpi_mae": {"greeting": 3.0}}  # MAE tripled
    result = compare_metrics(current=current, baseline=baseline)
    assert result.has_regression
    assert "kpi_mae.greeting" in result.regressions


def test_regression_result_has_diff() -> None:
    from scripts.regression_harness import compare_metrics

    baseline = {"wer": 0.10, "kpi_mae": {"greeting": 1.0}}
    current = {"wer": 0.20, "kpi_mae": {"greeting": 1.0}}
    result = compare_metrics(current=current, baseline=baseline)
    assert result.diff["wer"] == pytest.approx(0.10)


def test_empty_dataset_harness_is_skip() -> None:
    from scripts.regression_harness import run_harness

    with tempfile.TemporaryDirectory() as tmp:
        result = run_harness(
            datasets_dir=Path(tmp),
            baseline_file=Path(tmp) / "baseline.json",
        )

    assert result is None  # skip when no dataset


def test_harness_saves_baseline_on_first_run() -> None:
    from scripts.regression_harness import run_harness

    with tempfile.TemporaryDirectory() as tmp:
        ds = Path(tmp) / "ds"
        ds.mkdir()
        # Single entry
        entry_dir = ds / "call_001"
        entry_dir.mkdir()
        (entry_dir / "meta.json").write_text(json.dumps({"id": "call_001", "version": "1"}))
        (entry_dir / "golden_transcript.json").write_text(
            json.dumps({"full_text": "добрый день", "segments": [], "language": "ru"})
        )
        (entry_dir / "kpi_labels.json").write_text(
            json.dumps({"greeting": {"value": 8.0}})
        )

        baseline_file = Path(tmp) / "baseline.json"
        assert not baseline_file.exists()

        run_harness(datasets_dir=ds, baseline_file=baseline_file)

        assert baseline_file.exists()
        saved = json.loads(baseline_file.read_text())
        assert "wer" in saved


def test_harness_returns_warning_not_error_on_regression() -> None:
    from scripts.regression_harness import run_harness

    with tempfile.TemporaryDirectory() as tmp:
        ds = Path(tmp) / "ds"
        ds.mkdir()
        entry_dir = ds / "call_001"
        entry_dir.mkdir()
        (entry_dir / "meta.json").write_text(json.dumps({"id": "call_001", "version": "1"}))
        (entry_dir / "golden_transcript.json").write_text(
            json.dumps({"full_text": "добрый день", "segments": [], "language": "ru"})
        )
        (entry_dir / "kpi_labels.json").write_text(json.dumps({}))

        baseline_file = Path(tmp) / "baseline.json"
        _write_baseline(baseline_file, wer=0.001, kpi_mae={})  # very good baseline

        # harness should not raise, just warn
        result = run_harness(datasets_dir=ds, baseline_file=baseline_file)
        # Returns result (may have regression) but doesn't raise
        assert result is not None
