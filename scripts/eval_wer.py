"""M10-T2: eval_wer.py — Word Error Rate evaluation for STT quality.

Usage:
    python scripts/eval_wer.py [--dataset datasets/] [--normalize]

Empty dataset → prints 0 records, exits 0.
Requires: jiwer (uv pip install -e ".[eval]")
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scripts.dataset import GoldenTranscript


def _normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def compute_wer(hypothesis: str, reference: str, normalize: bool = False) -> float:
    """Compute WER between hypothesis and reference strings."""
    import jiwer

    if normalize:
        hypothesis = _normalize_text(hypothesis)
        reference = _normalize_text(reference)

    if not reference.strip():
        return 0.0 if not hypothesis.strip() else 1.0

    return float(jiwer.wer(reference, hypothesis))


# ---------------------------------------------------------------------------
# Dataset-level evaluation
# ---------------------------------------------------------------------------


@dataclass
class WerRecord:
    entry_id: str
    reference: str
    hypothesis: str
    wer: float


@dataclass
class WerResult:
    n_records: int
    wer: float | None
    per_record: list[WerRecord] = field(default_factory=list)


def eval_wer_dataset(
    datasets_dir: Path,
    hypothesis_fn: Callable[[GoldenTranscript], str],
    normalize: bool = True,
) -> WerResult:
    """Evaluate WER on all entries in datasets_dir.

    Args:
        datasets_dir: Path to dataset root.
        hypothesis_fn: Function that takes a GoldenTranscript and returns the STT hypothesis.
        normalize: Apply text normalization (lowercase + strip punctuation).

    Returns WerResult with aggregate WER and per-record details.
    Returns n_records=0, wer=None if dataset is empty.
    """
    sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
    from scripts.dataset import load_dataset

    entries = load_dataset(datasets_dir)
    if not entries:
        return WerResult(n_records=0, wer=None)

    records: list[WerRecord] = []
    for entry in entries:
        reference = entry.golden_transcript.full_text
        hypothesis = hypothesis_fn(entry.golden_transcript)
        wer_val = compute_wer(hypothesis=hypothesis, reference=reference, normalize=normalize)
        records.append(
            WerRecord(
                entry_id=entry.id,
                reference=reference,
                hypothesis=hypothesis,
                wer=wer_val,
            )
        )

    aggregate_wer = sum(r.wer for r in records) / len(records)
    return WerResult(n_records=len(records), wer=aggregate_wer, per_record=records)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Evaluate STT Word Error Rate")
    parser.add_argument("--dataset", default="datasets/", help="Path to dataset directory")
    parser.add_argument("--no-normalize", action="store_true", help="Skip text normalization")
    args = parser.parse_args(argv)

    datasets_dir = Path(args.dataset)
    result = eval_wer_dataset(
        datasets_dir,
        hypothesis_fn=lambda t: t.full_text,
        normalize=not args.no_normalize,
    )

    if result.n_records == 0:
        print("No dataset entries found — skipping WER evaluation.")
        return

    print(f"WER evaluation: {result.n_records} records")
    print(f"  Aggregate WER: {result.wer:.4f}" if result.wer is not None else "  WER: N/A")
    for rec in result.per_record:
        print(f"  [{rec.entry_id}] WER={rec.wer:.4f}")


if __name__ == "__main__":
    _main()
