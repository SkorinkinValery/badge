"""M10-T5: Few-shot example selector from labelled dataset.

Reads DatasetEntry items and converts them into few-shot examples
suitable for injecting into the LLM prompt via build_prompt(few_shot=...).

Empty dataset → returns []. Prompt builder handles empty list gracefully.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def load_few_shot_examples(
    datasets_dir: Path,
    n: int = 3,
) -> list[dict[str, Any]]:
    """Load up to n few-shot examples from the labelled dataset.

    Args:
        datasets_dir: Path to dataset root.
        n: Maximum number of examples to return.

    Returns list of {"transcript": str, "output": str} dicts.
    """
    sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
    from scripts.dataset import load_dataset

    entries = load_dataset(datasets_dir)
    if not entries:
        return []

    selected = entries[:n]
    examples: list[dict[str, Any]] = []

    for entry in selected:
        transcript_text = entry.golden_transcript.full_text
        output = {
            kpi_id: {
                "value": label.value,
                "quote": "",
                "comment": label.label or "",
            }
            for kpi_id, label in entry.kpi_labels.items()
        }
        examples.append(
            {
                "transcript": transcript_text,
                "output": json.dumps(output, ensure_ascii=False),
            }
        )

    return examples
