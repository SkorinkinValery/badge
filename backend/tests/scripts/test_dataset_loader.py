"""M10-T1: Dataset format + loader tests.

Tests run without any real audio files — all synthetic/in-memory.
Empty datasets/ → correct empty result, not error.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers — build fixture dataset on disk
# ---------------------------------------------------------------------------


def _write_sample_entry(base: Path, entry_id: str = "call_001") -> Path:
    entry_dir = base / entry_id
    entry_dir.mkdir(parents=True)

    meta = {
        "id": entry_id,
        "version": "1",
        "manager_id": "mgr-001",
        "script_id": None,
        "duration_sec": 120.5,
        "recorded_at": "2026-01-15T10:00:00Z",
    }
    (entry_dir / "meta.json").write_text(json.dumps(meta))

    golden = {
        "full_text": "Добрый день, чем могу помочь?",
        "segments": [
            {"start": 0.0, "end": 2.5, "text": "Добрый день,"},
            {"start": 2.5, "end": 4.0, "text": "чем могу помочь?"},
        ],
        "language": "ru",
    }
    (entry_dir / "golden_transcript.json").write_text(json.dumps(golden))

    kpi_labels = {
        "greeting": {"value": 8.0, "label": "Приветствие"},
        "needs_discovery": {"value": 6.0, "label": "Выявление потребности"},
    }
    (entry_dir / "kpi_labels.json").write_text(json.dumps(kpi_labels))

    return entry_dir


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_load_single_entry() -> None:
    from scripts.dataset import DatasetEntry, load_dataset

    with tempfile.TemporaryDirectory() as tmp:
        _write_sample_entry(Path(tmp), "call_001")
        entries = load_dataset(Path(tmp))

    assert len(entries) == 1
    entry = entries[0]
    assert isinstance(entry, DatasetEntry)
    assert entry.id == "call_001"


def test_entry_has_golden_transcript() -> None:
    from scripts.dataset import load_dataset

    with tempfile.TemporaryDirectory() as tmp:
        _write_sample_entry(Path(tmp))
        entries = load_dataset(Path(tmp))

    assert entries[0].golden_transcript is not None
    assert "Добрый день" in entries[0].golden_transcript.full_text
    assert len(entries[0].golden_transcript.segments) == 2


def test_entry_has_kpi_labels() -> None:
    from scripts.dataset import load_dataset

    with tempfile.TemporaryDirectory() as tmp:
        _write_sample_entry(Path(tmp))
        entries = load_dataset(Path(tmp))

    labels = entries[0].kpi_labels
    assert "greeting" in labels
    assert labels["greeting"].value == 8.0


def test_empty_dataset_returns_empty_list() -> None:
    from scripts.dataset import load_dataset

    with tempfile.TemporaryDirectory() as tmp:
        entries = load_dataset(Path(tmp))

    assert entries == []


def test_missing_dataset_dir_returns_empty() -> None:
    from scripts.dataset import load_dataset

    entries = load_dataset(Path("/nonexistent/datasets/path"))
    assert entries == []


def test_multiple_entries_loaded() -> None:
    from scripts.dataset import load_dataset

    with tempfile.TemporaryDirectory() as tmp:
        _write_sample_entry(Path(tmp), "call_001")
        _write_sample_entry(Path(tmp), "call_002")
        entries = load_dataset(Path(tmp))

    assert len(entries) == 2
    ids = {e.id for e in entries}
    assert ids == {"call_001", "call_002"}


def test_invalid_kpi_key_raises() -> None:
    from scripts.dataset import load_dataset

    with tempfile.TemporaryDirectory() as tmp:
        entry_dir = Path(tmp) / "bad_entry"
        entry_dir.mkdir()
        (entry_dir / "meta.json").write_text(json.dumps({"id": "bad_entry", "version": "1"}))
        (entry_dir / "golden_transcript.json").write_text(
            json.dumps({"full_text": "test", "segments": [], "language": "ru"})
        )
        (entry_dir / "kpi_labels.json").write_text(
            json.dumps({"NONEXISTENT_KPI_KEY_XYZ": {"value": 5.0}})
        )
        with pytest.raises((ValueError, KeyError)):
            load_dataset(Path(tmp))


def test_entry_kpi_keys_match_kpi_yaml() -> None:
    from scripts.dataset import load_dataset

    from app.config.kpi import load_kpi_config

    with tempfile.TemporaryDirectory() as tmp:
        _write_sample_entry(Path(tmp))
        entries = load_dataset(Path(tmp))

    kpi_cfg = load_kpi_config()
    known_ids = {kpi.id for kpi in kpi_cfg.kpis}
    for key in entries[0].kpi_labels:
        assert key in known_ids, f"kpi label key '{key}' not in kpi.yaml"


def test_entry_segments_have_monotone_timecodes() -> None:
    from scripts.dataset import load_dataset

    with tempfile.TemporaryDirectory() as tmp:
        _write_sample_entry(Path(tmp))
        entries = load_dataset(Path(tmp))

    segs = entries[0].golden_transcript.segments
    for i in range(len(segs) - 1):
        assert segs[i].end <= segs[i + 1].start or segs[i].end <= segs[i + 1].end
