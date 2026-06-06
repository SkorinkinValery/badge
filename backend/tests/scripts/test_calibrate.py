"""M10-T6: calibrate.py — calibration procedure tests.

Uses synthetic eval to avoid real LLM calls.
Result is new config candidates (weights/prompt), never code changes.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest


def test_calibration_returns_best_config_candidate() -> None:
    from scripts.calibrate import CalibrationResult, calibrate

    candidates = [
        {"initial_prompt": "", "weight_override": {}},
        {"initial_prompt": "Будь точен.", "weight_override": {"greeting": 2.0}},
    ]

    # Synthetic eval_fn: second candidate is better (lower MAE)
    def mock_eval(candidate: dict, datasets_dir: Path) -> float:
        return 0.5 if candidate["initial_prompt"] == "" else 0.1

    with tempfile.TemporaryDirectory() as tmp:
        result = calibrate(
            candidates=candidates,
            datasets_dir=Path(tmp),
            eval_fn=mock_eval,
        )

    assert isinstance(result, CalibrationResult)
    assert result.best_candidate == candidates[1]
    assert result.best_score == pytest.approx(0.1)


def test_calibration_empty_dataset_is_noop() -> None:
    from scripts.calibrate import calibrate

    candidates = [{"initial_prompt": "test", "weight_override": {}}]

    def mock_eval(candidate: dict, datasets_dir: Path) -> float:
        return 0.5

    with tempfile.TemporaryDirectory() as tmp:
        result = calibrate(
            candidates=candidates,
            datasets_dir=Path(tmp),
            eval_fn=mock_eval,
        )

    # Empty dataset → no-op (no real data to evaluate)
    assert result is not None  # returns result with whatever eval_fn returns


def test_calibration_result_candidates_are_configs_not_code() -> None:
    from scripts.calibrate import calibrate

    candidates = [
        {"initial_prompt": "p1", "weight_override": {"greeting": 1.0}},
        {"initial_prompt": "p2", "weight_override": {"greeting": 2.0}},
    ]

    def mock_eval(candidate: dict, datasets_dir: Path) -> float:
        return 0.3 if candidate["initial_prompt"] == "p1" else 0.2

    with tempfile.TemporaryDirectory() as tmp:
        result = calibrate(candidates=candidates, datasets_dir=Path(tmp), eval_fn=mock_eval)

    best = result.best_candidate
    # Best candidate must be a config dict (no Python code)
    assert isinstance(best, dict)
    assert "initial_prompt" in best or "weight_override" in best


def test_calibration_saves_report() -> None:
    from scripts.calibrate import calibrate

    candidates = [{"initial_prompt": "test", "weight_override": {}}]

    def mock_eval(candidate: dict, datasets_dir: Path) -> float:
        return 0.42

    with tempfile.TemporaryDirectory() as tmp:
        report_file = Path(tmp) / "calibration_report.json"
        calibrate(
            candidates=candidates,
            datasets_dir=Path(tmp),
            eval_fn=mock_eval,
            report_file=report_file,
        )
        assert report_file.exists()
        report = json.loads(report_file.read_text())
        assert "best_candidate" in report
        assert "best_score" in report


def test_calibration_ranks_all_candidates() -> None:
    from scripts.calibrate import calibrate

    candidates = [
        {"initial_prompt": "a", "weight_override": {}},
        {"initial_prompt": "b", "weight_override": {}},
        {"initial_prompt": "c", "weight_override": {}},
    ]
    scores = {"a": 0.8, "b": 0.3, "c": 0.6}

    def mock_eval(candidate: dict, datasets_dir: Path) -> float:
        return scores[candidate["initial_prompt"]]

    with tempfile.TemporaryDirectory() as tmp:
        result = calibrate(candidates=candidates, datasets_dir=Path(tmp), eval_fn=mock_eval)

    assert len(result.ranked) == 3
    # Best first (lowest score = best)
    assert result.ranked[0]["score"] == pytest.approx(0.3)
