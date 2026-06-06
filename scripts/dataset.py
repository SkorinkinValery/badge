"""M10-T1: Dataset loader for eval scripts.

Dataset layout (datasets/<entry_id>/):
  meta.json             — entry metadata (id, version, manager_id, ...)
  golden_transcript.json — ground-truth transcript with segments
  kpi_labels.json       — manual KPI annotation {kpi_id: {value, label}}
  audio.wav             — optional (large, .gitignored)

Empty or missing datasets/ → returns [], never raises.
Unknown KPI keys → raises ValueError (catches schema drift vs kpi.yaml).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_DATASETS_DIR = Path(__file__).parent.parent / "datasets"

# KPI ids known to the system — validated against kpi.yaml at load time
_KNOWN_KPI_IDS: set[str] | None = None

FORMAT_VERSION = "1"


def _known_kpi_ids() -> set[str]:
    global _KNOWN_KPI_IDS
    if _KNOWN_KPI_IDS is None:
        sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
        from app.config.kpi import load_kpi_config

        cfg = load_kpi_config()
        _KNOWN_KPI_IDS = {k.id for k in cfg.kpis}
    return _KNOWN_KPI_IDS


class GoldenSegment(BaseModel):
    model_config = ConfigDict(frozen=True)

    start: float
    end: float
    text: str


class GoldenTranscript(BaseModel):
    model_config = ConfigDict(frozen=True)

    full_text: str
    segments: list[GoldenSegment]
    language: str = "ru"


class KpiLabel(BaseModel):
    model_config = ConfigDict(frozen=True)

    value: float
    label: str = ""

    @field_validator("value")
    @classmethod
    def validate_value(cls, v: float) -> float:
        if not (0.0 <= v <= 10.0):
            raise ValueError(f"KPI label value must be in [0, 10], got {v}")
        return v


class EntryMeta(BaseModel):
    id: str
    version: str = FORMAT_VERSION
    manager_id: str = ""
    script_id: str | None = None
    duration_sec: float = 0.0
    recorded_at: str = ""


class DatasetEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    meta: EntryMeta
    golden_transcript: GoldenTranscript
    kpi_labels: dict[str, KpiLabel]


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


def load_dataset(datasets_dir: Path = _DATASETS_DIR) -> list[DatasetEntry]:
    """Load all entries from datasets_dir.

    Returns empty list if directory doesn't exist or is empty.
    Raises ValueError for unknown KPI keys (schema drift guard).
    """
    if not datasets_dir.exists() or not datasets_dir.is_dir():
        return []

    known = _known_kpi_ids()
    entries: list[DatasetEntry] = []

    for entry_dir in sorted(datasets_dir.iterdir()):
        if not entry_dir.is_dir():
            continue

        meta_file = entry_dir / "meta.json"
        transcript_file = entry_dir / "golden_transcript.json"
        labels_file = entry_dir / "kpi_labels.json"

        if not (meta_file.exists() and transcript_file.exists() and labels_file.exists()):
            continue

        meta_data: dict[str, Any] = json.loads(meta_file.read_text())
        meta = EntryMeta.model_validate(meta_data)

        transcript_data: dict[str, Any] = json.loads(transcript_file.read_text())
        golden = GoldenTranscript.model_validate(transcript_data)

        labels_raw: dict[str, Any] = json.loads(labels_file.read_text())
        for key in labels_raw:
            if key not in known:
                raise ValueError(
                    f"Unknown KPI key '{key}' in {labels_file}. "
                    f"Known: {sorted(known)}"
                )
        kpi_labels = {k: KpiLabel.model_validate(v) for k, v in labels_raw.items()}

        entries.append(
            DatasetEntry(
                id=entry_dir.name,
                meta=meta,
                golden_transcript=golden,
                kpi_labels=kpi_labels,
            )
        )

    return entries
