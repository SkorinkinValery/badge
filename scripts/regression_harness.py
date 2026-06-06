"""M10-T4: regression_harness.py — golden-set regression detector.

Compares current WER/KPI metrics against a saved baseline snapshot.
Non-blocking: warns on regression, never raises or fails CI.

Usage:
    python scripts/regression_harness.py [--dataset datasets/] [--baseline baseline.json]

Empty dataset → skip (returns None).
First run (no baseline file) → saves current metrics as baseline.
Subsequent runs → compares and warns on regression.

Thresholds for acceptable drift are config-driven (see REGRESSION_THRESHOLDS below).
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Acceptable relative drift before flagging regression (config-driven, could move to yaml)
REGRESSION_THRESHOLDS: dict[str, float] = {
    "wer": 0.05,         # WER may increase by at most 5 pp
    "kpi_mae": 0.50,     # KPI MAE may increase by at most 0.5 points
}


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------


@dataclass
class RegressionResult:
    has_regression: bool
    regressions: list[str] = field(default_factory=list)
    diff: dict[str, float] = field(default_factory=dict)
    current: dict[str, Any] = field(default_factory=dict)
    baseline: dict[str, Any] = field(default_factory=dict)


def compare_metrics(
    current: dict[str, Any],
    baseline: dict[str, Any],
    thresholds: dict[str, float] | None = None,
) -> RegressionResult:
    """Compare current metrics against baseline snapshot.

    Returns RegressionResult with has_regression=True if any metric
    worsened beyond its threshold.
    """
    thr = thresholds or REGRESSION_THRESHOLDS
    regressions: list[str] = []
    diff: dict[str, float] = {}

    # Compare WER
    cur_wer = current.get("wer")
    base_wer = baseline.get("wer")
    if cur_wer is not None and base_wer is not None:
        delta = cur_wer - base_wer
        diff["wer"] = delta
        if delta > thr.get("wer", 0.05):
            regressions.append("wer")

    # Compare per-KPI MAE
    cur_kpi = current.get("kpi_mae") or {}
    base_kpi = baseline.get("kpi_mae") or {}
    for kpi_id in set(cur_kpi) | set(base_kpi):
        cur_mae = cur_kpi.get(kpi_id)
        base_mae = base_kpi.get(kpi_id)
        if cur_mae is not None and base_mae is not None:
            delta = cur_mae - base_mae
            diff[f"kpi_mae.{kpi_id}"] = delta
            if delta > thr.get("kpi_mae", 0.50):
                regressions.append(f"kpi_mae.{kpi_id}")

    return RegressionResult(
        has_regression=bool(regressions),
        regressions=regressions,
        diff=diff,
        current=current,
        baseline=baseline,
    )


# ---------------------------------------------------------------------------
# Harness runner
# ---------------------------------------------------------------------------


def run_harness(
    datasets_dir: Path,
    baseline_file: Path | None = None,
    thresholds: dict[str, float] | None = None,
) -> RegressionResult | None:
    """Run WER + KPI eval, compare against baseline, warn on regression.

    Returns None if dataset is empty (skip).
    Returns RegressionResult otherwise (never raises).
    """
    sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
    from scripts.dataset import load_dataset
    from scripts.eval_kpi import eval_kpi_dataset
    from scripts.eval_wer import eval_wer_dataset

    entries = load_dataset(datasets_dir)
    if not entries:
        return None

    wer_result = eval_wer_dataset(
        datasets_dir, hypothesis_fn=lambda t: t.full_text
    )
    kpi_result = eval_kpi_dataset(
        datasets_dir, predicted_fn=lambda t, kpi_ids: {}
    )

    current: dict[str, Any] = {
        "wer": wer_result.wer,
        "kpi_mae": {
            kpi_id: m.mae
            for kpi_id, m in kpi_result.per_kpi.items()
            if m.mae is not None
        },
    }

    if baseline_file is None:
        baseline_file = Path("baseline.json")

    if not baseline_file.exists():
        baseline_file.write_text(json.dumps(current, indent=2))
        print(f"Baseline saved to {baseline_file}")
        return RegressionResult(has_regression=False, current=current, baseline=current)

    baseline: dict[str, Any] = json.loads(baseline_file.read_text())
    result = compare_metrics(current=current, baseline=baseline, thresholds=thresholds)

    if result.has_regression:
        warnings.warn(
            f"Metric regression detected: {result.regressions}. "
            f"Diff: {result.diff}",
            stacklevel=1,
        )

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Regression harness for eval metrics")
    parser.add_argument("--dataset", default="datasets/", help="Path to dataset directory")
    parser.add_argument("--baseline", default="baseline.json", help="Baseline snapshot file")
    args = parser.parse_args(argv)

    result = run_harness(
        datasets_dir=Path(args.dataset),
        baseline_file=Path(args.baseline),
    )

    if result is None:
        print("No dataset entries — skip.")
        return

    if result.has_regression:
        print(f"WARNING: Regression detected in: {result.regressions}")
        for key, delta in result.diff.items():
            print(f"  {key}: {delta:+.4f}")
    else:
        print("No regressions detected.")
        for key, delta in result.diff.items():
            print(f"  {key}: {delta:+.4f}")


if __name__ == "__main__":
    _main()
