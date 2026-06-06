"""M10-T3: eval_kpi.py — KPI quality evaluation (accuracy/F1/MAE).

Usage:
    python scripts/eval_kpi.py [--dataset datasets/]

Empty dataset → prints 0 records, exits 0.
fact-KPI (binary 0/10): precision/recall/F1.
scale-KPI: MAE + tolerance-accuracy (|pred-gold| <= 1).
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scripts.dataset import GoldenTranscript


# ---------------------------------------------------------------------------
# Per-KPI metric record
# ---------------------------------------------------------------------------


@dataclass
class KpiMetric:
    kpi_id: str
    n_samples: int = 0
    mae: float | None = None
    accuracy: float | None = None
    # Fact KPI fields
    precision: float | None = None
    recall: float | None = None
    f1: float | None = None


def compute_kpi_metrics(
    predicted: dict[str, float],
    gold: dict[str, float],
    fact_kpi_ids: set[str] | None = None,
) -> dict[str, KpiMetric]:
    """Compute per-KPI metrics for a single record.

    Returns dict of kpi_id → KpiMetric.
    Missing predictions treated as None (not counted).
    """
    fact_ids = fact_kpi_ids or set()
    result: dict[str, KpiMetric] = {}

    for kpi_id, gold_val in gold.items():
        metric = KpiMetric(kpi_id=kpi_id, n_samples=1)
        pred_val = predicted.get(kpi_id)

        if pred_val is None:
            result[kpi_id] = metric
            continue

        if kpi_id in fact_ids:
            # fact KPI: 10 = positive, 0 = negative
            pred_pos = pred_val >= 5.0
            gold_pos = gold_val >= 5.0
            tp = int(pred_pos and gold_pos)
            fp = int(pred_pos and not gold_pos)
            fn = int(not pred_pos and gold_pos)
            metric.precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            metric.recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            if (metric.precision + metric.recall) > 0:
                metric.f1 = (
                    2 * metric.precision * metric.recall
                    / (metric.precision + metric.recall)
                )
            else:
                metric.f1 = 0.0
        else:
            metric.mae = abs(pred_val - gold_val)
            metric.accuracy = 1.0 if abs(pred_val - gold_val) <= 1.0 else 0.0

        result[kpi_id] = metric

    return result


# ---------------------------------------------------------------------------
# Dataset-level evaluation
# ---------------------------------------------------------------------------


@dataclass
class KpiEvalResult:
    n_records: int
    per_kpi: dict[str, KpiMetric] = field(default_factory=dict)


def eval_kpi_dataset(
    datasets_dir: Path,
    predicted_fn: Callable[[GoldenTranscript, set[str]], dict[str, float]],
    fact_kpi_ids: set[str] | None = None,
) -> KpiEvalResult:
    """Evaluate KPI quality on all entries in datasets_dir.

    Args:
        datasets_dir: Path to dataset root.
        predicted_fn: Function(transcript, kpi_ids) → {kpi_id: predicted_value}.
        fact_kpi_ids: KPI ids that are binary (fact type).
    """
    sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
    from scripts.dataset import load_dataset

    entries = load_dataset(datasets_dir)
    if not entries:
        return KpiEvalResult(n_records=0)

    # Accumulate metrics per KPI across all records
    accumulated: dict[str, list[KpiMetric]] = {}

    for entry in entries:
        kpi_ids = set(entry.kpi_labels.keys())
        gold = {k: v.value for k, v in entry.kpi_labels.items()}
        predicted = predicted_fn(entry.golden_transcript, kpi_ids)
        record_metrics = compute_kpi_metrics(predicted, gold, fact_kpi_ids=fact_kpi_ids)

        for kpi_id, metric in record_metrics.items():
            accumulated.setdefault(kpi_id, []).append(metric)

    # Aggregate per KPI
    aggregated: dict[str, KpiMetric] = {}
    for kpi_id, metrics in accumulated.items():
        agg = KpiMetric(kpi_id=kpi_id, n_samples=len(metrics))
        mae_vals = [m.mae for m in metrics if m.mae is not None]
        acc_vals = [m.accuracy for m in metrics if m.accuracy is not None]
        f1_vals = [m.f1 for m in metrics if m.f1 is not None]
        prec_vals = [m.precision for m in metrics if m.precision is not None]
        rec_vals = [m.recall for m in metrics if m.recall is not None]

        if mae_vals:
            agg.mae = sum(mae_vals) / len(mae_vals)
        if acc_vals:
            agg.accuracy = sum(acc_vals) / len(acc_vals)
        if f1_vals:
            agg.f1 = sum(f1_vals) / len(f1_vals)
        if prec_vals:
            agg.precision = sum(prec_vals) / len(prec_vals)
        if rec_vals:
            agg.recall = sum(rec_vals) / len(rec_vals)

        aggregated[kpi_id] = agg

    return KpiEvalResult(n_records=len(entries), per_kpi=aggregated)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Evaluate KPI prediction quality")
    parser.add_argument("--dataset", default="datasets/", help="Path to dataset directory")
    args = parser.parse_args(argv)

    result = eval_kpi_dataset(
        Path(args.dataset),
        predicted_fn=lambda t, kpi_ids: {},  # placeholder — real eval needs Analyzer
    )

    if result.n_records == 0:
        print("No dataset entries found — skipping KPI evaluation.")
        return

    print(f"KPI evaluation: {result.n_records} records")
    for kpi_id, metric in sorted(result.per_kpi.items()):
        parts = [f"  [{kpi_id}]"]
        if metric.mae is not None:
            parts.append(f"MAE={metric.mae:.2f}")
        if metric.accuracy is not None:
            parts.append(f"acc(±1)={metric.accuracy:.2%}")
        if metric.f1 is not None:
            parts.append(f"F1={metric.f1:.2f}")
        print(" ".join(parts))


if __name__ == "__main__":
    _main()
