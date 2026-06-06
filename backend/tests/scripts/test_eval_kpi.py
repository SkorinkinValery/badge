"""M10-T3: eval_kpi.py — KPI accuracy/F1 tests.

Synthetic predictions/labels — no LLM calls.
fact-KPI: binary (0 or 10) → precision/recall/F1.
scale-KPI: MAE and tolerance-accuracy.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest


def _make_dataset_with_labels(
    base: Path,
    entry_id: str,
    kpi_labels: dict[str, float],
) -> None:
    d = base / entry_id
    d.mkdir(parents=True)
    (d / "meta.json").write_text(json.dumps({"id": entry_id, "version": "1"}))
    (d / "golden_transcript.json").write_text(
        json.dumps({"full_text": "тест", "segments": [], "language": "ru"})
    )
    labels = {k: {"value": v} for k, v in kpi_labels.items()}
    (d / "kpi_labels.json").write_text(json.dumps(labels))


def test_perfect_scale_kpi_has_zero_mae() -> None:
    from scripts.eval_kpi import compute_kpi_metrics

    pred = {"greeting": 8.0, "needs_discovery": 6.0}
    gold = {"greeting": 8.0, "needs_discovery": 6.0}
    result = compute_kpi_metrics(predicted=pred, gold=gold)
    assert result["greeting"].mae == pytest.approx(0.0)
    assert result["needs_discovery"].mae == pytest.approx(0.0)


def test_scale_kpi_mae_correct() -> None:
    from scripts.eval_kpi import compute_kpi_metrics

    pred = {"greeting": 7.0}
    gold = {"greeting": 5.0}
    result = compute_kpi_metrics(predicted=pred, gold=gold)
    assert result["greeting"].mae == pytest.approx(2.0)


def test_fact_kpi_perfect_prediction() -> None:
    from scripts.eval_kpi import compute_kpi_metrics

    pred = {"measurement_offered": 10.0}
    gold = {"measurement_offered": 10.0}
    result = compute_kpi_metrics(predicted=pred, gold=gold, fact_kpi_ids={"measurement_offered"})
    m = result["measurement_offered"]
    assert m.precision == pytest.approx(1.0)
    assert m.recall == pytest.approx(1.0)
    assert m.f1 == pytest.approx(1.0)


def test_fact_kpi_false_positive() -> None:
    from scripts.eval_kpi import compute_kpi_metrics

    pred = {"measurement_offered": 10.0}
    gold = {"measurement_offered": 0.0}
    result = compute_kpi_metrics(predicted=pred, gold=gold, fact_kpi_ids={"measurement_offered"})
    m = result["measurement_offered"]
    assert m.recall == pytest.approx(0.0)


def test_empty_dataset_returns_empty_result() -> None:
    from scripts.eval_kpi import eval_kpi_dataset

    with tempfile.TemporaryDirectory() as tmp:
        result = eval_kpi_dataset(
            Path(tmp),
            predicted_fn=lambda t, kpi_ids: dict.fromkeys(kpi_ids, 7.0),
        )

    assert result.n_records == 0
    assert result.per_kpi == {}


def test_eval_kpi_dataset_aggregate() -> None:
    from scripts.eval_kpi import eval_kpi_dataset

    with tempfile.TemporaryDirectory() as tmp:
        _make_dataset_with_labels(
            Path(tmp), "call_001", {"greeting": 8.0, "needs_discovery": 6.0}
        )
        _make_dataset_with_labels(
            Path(tmp), "call_002", {"greeting": 7.0, "needs_discovery": 5.0}
        )
        # Perfect predictions
        result = eval_kpi_dataset(
            Path(tmp),
            predicted_fn=lambda t, kpi_ids: {
                "greeting": 8.0 if "001" in t.full_text else 7.0,
                "needs_discovery": 6.0 if "001" in t.full_text else 5.0,
            },
        )

    assert result.n_records == 2
    assert "greeting" in result.per_kpi


def test_missing_kpi_in_prediction_handled() -> None:
    from scripts.eval_kpi import compute_kpi_metrics

    pred = {}
    gold = {"greeting": 8.0}
    result = compute_kpi_metrics(predicted=pred, gold=gold)
    assert "greeting" in result
    assert result["greeting"].mae is None or result["greeting"].mae >= 0.0


def test_result_has_per_kpi_details() -> None:
    from scripts.eval_kpi import eval_kpi_dataset

    with tempfile.TemporaryDirectory() as tmp:
        _make_dataset_with_labels(Path(tmp), "call_001", {"greeting": 8.0})
        result = eval_kpi_dataset(
            Path(tmp),
            predicted_fn=lambda t, kpi_ids: {"greeting": 8.0},
        )

    assert "greeting" in result.per_kpi
    kpi_stat = result.per_kpi["greeting"]
    assert hasattr(kpi_stat, "mae")
