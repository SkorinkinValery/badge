"""M10-T2: eval_wer.py — WER calculation tests.

Tests use synthetic data — no real audio or model calls.
Empty dataset → skip (0 records), not failure.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest


def _make_dataset(base: Path, entries: list[tuple[str, str]]) -> None:
    """Create synthetic dataset entries: (entry_id, golden_text)."""
    for entry_id, text in entries:
        d = base / entry_id
        d.mkdir(parents=True)
        (d / "meta.json").write_text(json.dumps({"id": entry_id, "version": "1"}))
        (d / "golden_transcript.json").write_text(
            json.dumps({"full_text": text, "segments": [], "language": "ru"})
        )
        (d / "kpi_labels.json").write_text(json.dumps({}))


def test_perfect_match_wer_is_zero() -> None:
    from scripts.eval_wer import compute_wer

    wer = compute_wer(hypothesis="добрый день", reference="добрый день")
    assert wer == pytest.approx(0.0)


def test_full_substitution_wer_is_one() -> None:
    from scripts.eval_wer import compute_wer

    wer = compute_wer(hypothesis="один два три", reference="четыре пять шесть")
    assert wer == pytest.approx(1.0)


def test_partial_error_wer_between_zero_and_one() -> None:
    from scripts.eval_wer import compute_wer

    wer = compute_wer(hypothesis="добрый день ошибка", reference="добрый день правильно")
    assert 0.0 < wer < 1.0


def test_text_normalization_lowercases() -> None:
    from scripts.eval_wer import compute_wer

    wer = compute_wer(hypothesis="Добрый День", reference="добрый день", normalize=True)
    assert wer == pytest.approx(0.0)


def test_text_normalization_strips_punctuation() -> None:
    from scripts.eval_wer import compute_wer

    wer = compute_wer(hypothesis="добрый, день!", reference="добрый день", normalize=True)
    assert wer == pytest.approx(0.0)


def test_eval_wer_on_empty_dataset_returns_zero_records() -> None:
    from scripts.eval_wer import eval_wer_dataset

    with tempfile.TemporaryDirectory() as tmp:
        result = eval_wer_dataset(Path(tmp), hypothesis_fn=lambda t: t.full_text)

    assert result.n_records == 0
    assert result.wer is None


def test_eval_wer_aggregate_over_multiple_records() -> None:
    from scripts.eval_wer import eval_wer_dataset

    with tempfile.TemporaryDirectory() as tmp:
        _make_dataset(
            Path(tmp),
            [
                ("call_001", "добрый день"),
                ("call_002", "здравствуйте"),
            ],
        )
        # hypothesis_fn returns perfect match for all
        result = eval_wer_dataset(
            Path(tmp), hypothesis_fn=lambda t: t.full_text
        )

    assert result.n_records == 2
    assert result.wer == pytest.approx(0.0)


def test_eval_wer_with_errors_aggregate() -> None:
    from scripts.eval_wer import eval_wer_dataset

    with tempfile.TemporaryDirectory() as tmp:
        _make_dataset(Path(tmp), [("call_001", "добрый день")])
        result = eval_wer_dataset(
            Path(tmp),
            hypothesis_fn=lambda t: "неверный текст полностью",
        )

    assert result.n_records == 1
    assert result.wer is not None and result.wer > 0.0


def test_wer_result_has_per_record_detail() -> None:
    from scripts.eval_wer import eval_wer_dataset

    with tempfile.TemporaryDirectory() as tmp:
        _make_dataset(Path(tmp), [("call_001", "добрый день"), ("call_002", "пока")])
        result = eval_wer_dataset(
            Path(tmp), hypothesis_fn=lambda t: t.full_text
        )

    assert len(result.per_record) == 2
    assert all(r.entry_id for r in result.per_record)
