"""M10-T7: CI eval guard tests.

Verifies that all eval scripts exit 0 (skip) when dataset is missing/empty.
Verifies CI job config has continue-on-error: true.
"""

from __future__ import annotations

import tempfile
from pathlib import Path


def test_eval_wer_no_dataset_exits_cleanly() -> None:
    from scripts.eval_wer import eval_wer_dataset

    with tempfile.TemporaryDirectory() as tmp:
        result = eval_wer_dataset(Path(tmp), hypothesis_fn=lambda t: t.full_text)

    assert result.n_records == 0
    assert result.wer is None


def test_eval_kpi_no_dataset_exits_cleanly() -> None:
    from scripts.eval_kpi import eval_kpi_dataset

    with tempfile.TemporaryDirectory() as tmp:
        result = eval_kpi_dataset(Path(tmp), predicted_fn=lambda t, kpi_ids: {})

    assert result.n_records == 0
    assert result.per_kpi == {}


def test_regression_harness_no_dataset_returns_none() -> None:
    from scripts.regression_harness import run_harness

    with tempfile.TemporaryDirectory() as tmp:
        result = run_harness(datasets_dir=Path(tmp))

    assert result is None


def test_few_shot_no_dataset_returns_empty() -> None:
    from scripts.few_shot import load_few_shot_examples

    with tempfile.TemporaryDirectory() as tmp:
        examples = load_few_shot_examples(Path(tmp), n=3)

    assert examples == []


def test_ci_yml_eval_job_is_non_critical() -> None:
    """CI eval job must have continue-on-error: true."""
    import yaml

    ci_file = Path(__file__).parent.parent.parent.parent / ".github" / "workflows" / "ci.yml"
    assert ci_file.exists(), "ci.yml not found"

    with open(ci_file) as f:
        cfg = yaml.safe_load(f)

    eval_job = cfg.get("jobs", {}).get("eval", {})
    assert eval_job.get("continue-on-error") is True, (
        "eval job must have continue-on-error: true to be non-blocking"
    )


def test_ci_yml_eval_runs_regression_harness() -> None:
    """CI eval job should include regression harness step."""
    import yaml

    ci_file = Path(__file__).parent.parent.parent.parent / ".github" / "workflows" / "ci.yml"
    with open(ci_file) as f:
        cfg = yaml.safe_load(f)

    eval_job = cfg.get("jobs", {}).get("eval", {})
    steps = eval_job.get("steps", [])
    all_run_scripts = " ".join(
        step.get("run", "") for step in steps if "run" in step
    )
    assert "regression_harness" in all_run_scripts, (
        "eval CI job must run regression_harness.py"
    )
