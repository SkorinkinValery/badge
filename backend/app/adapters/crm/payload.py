"""Common export payload serializer for all CRM adapters (M8-T1).

All exporters call `build_export_payload` to get a stable dict
that can be serialised to JSON and mapped to any target system.
"""

from __future__ import annotations

from typing import Any

from app.core.domain import Recording
from app.core.ports.analyzer import AnalysisResult


def build_export_payload(
    analysis: AnalysisResult,
    recording: Recording,
    score: float | None = None,
    verdict: str | None = None,
) -> dict[str, Any]:
    """Build a stable export payload from analysis + recording metadata.

    Keys are stable across exporters — each adapter maps them to its own schema.
    """
    return {
        "recording_id": str(recording.id),
        "manager_id": str(recording.manager_id),
        "channel": recording.channel,
        "created_at": recording.created_at.isoformat(),
        "summary": analysis.summary,
        "kpi_json": analysis.kpi_json,
        "score": score,
        "verdict": verdict,
    }
