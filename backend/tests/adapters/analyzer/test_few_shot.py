"""M10-T5: Few-shot from dataset into prompt.

Verifies few-shot selector reads examples from dataset and injects them
into the prompt. Empty dataset → prompt without few-shot (no error).
"""

from __future__ import annotations

import json
import tempfile
import uuid
from pathlib import Path

from app.core.domain.transcript import Segment, Transcript


def _make_transcript(text: str = "Добрый день") -> Transcript:
    return Transcript(
        id=uuid.uuid4(),
        recording_id=uuid.uuid4(),
        full_text=text,
        segments=(Segment(start=0.0, end=2.0, text=text),),
        detected_language="ru",
    )


def _write_entry(base: Path, entry_id: str, transcript_text: str, kpi: dict) -> None:
    d = base / entry_id
    d.mkdir(parents=True)
    (d / "meta.json").write_text(json.dumps({"id": entry_id, "version": "1"}))
    (d / "golden_transcript.json").write_text(
        json.dumps({"full_text": transcript_text, "segments": [], "language": "ru"})
    )
    (d / "kpi_labels.json").write_text(json.dumps({k: {"value": v} for k, v in kpi.items()}))


def test_empty_dataset_prompt_has_no_few_shot() -> None:
    from scripts.few_shot import load_few_shot_examples

    from app.adapters.analyzer.prompt import build_prompt

    with tempfile.TemporaryDirectory() as tmp:
        examples = load_few_shot_examples(Path(tmp), n=3)

    transcript = _make_transcript()
    system, _ = build_prompt(transcript, few_shot=examples)
    assert "Примеры оценки" not in system


def test_dataset_examples_injected_into_prompt() -> None:
    from scripts.few_shot import load_few_shot_examples

    from app.adapters.analyzer.prompt import build_prompt

    with tempfile.TemporaryDirectory() as tmp:
        _write_entry(Path(tmp), "call_001", "Добрый день, чем помочь?", {"greeting": 8.0})
        examples = load_few_shot_examples(Path(tmp), n=3)

    transcript = _make_transcript()
    system, _ = build_prompt(transcript, few_shot=examples)
    assert "Примеры оценки" in system
    assert "Добрый день, чем помочь?" in system


def test_few_shot_count_respects_n_param() -> None:
    from scripts.few_shot import load_few_shot_examples

    with tempfile.TemporaryDirectory() as tmp:
        for i in range(5):
            _write_entry(Path(tmp), f"call_{i:03d}", f"Текст {i}", {"greeting": float(i)})
        examples = load_few_shot_examples(Path(tmp), n=3)

    assert len(examples) == 3


def test_few_shot_more_than_available_returns_all() -> None:
    from scripts.few_shot import load_few_shot_examples

    with tempfile.TemporaryDirectory() as tmp:
        _write_entry(Path(tmp), "call_001", "Один", {"greeting": 8.0})
        examples = load_few_shot_examples(Path(tmp), n=10)

    assert len(examples) == 1


def test_few_shot_example_has_transcript_and_output() -> None:
    from scripts.few_shot import load_few_shot_examples

    with tempfile.TemporaryDirectory() as tmp:
        _write_entry(Path(tmp), "call_001", "Добрый день", {"greeting": 8.0})
        examples = load_few_shot_examples(Path(tmp), n=3)

    assert "transcript" in examples[0]
    assert "output" in examples[0]
    assert examples[0]["transcript"]
    assert examples[0]["output"]


def test_few_shot_output_is_valid_json() -> None:
    from scripts.few_shot import load_few_shot_examples

    with tempfile.TemporaryDirectory() as tmp:
        _write_entry(Path(tmp), "call_001", "Добрый день", {"greeting": 8.0})
        examples = load_few_shot_examples(Path(tmp), n=1)

    output = examples[0]["output"]
    parsed = json.loads(output)
    assert isinstance(parsed, dict)
