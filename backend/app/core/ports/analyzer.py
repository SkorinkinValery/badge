"""Analyzer port and AnalysisResult DTO.

The interface is designed for future map-reduce over chunks for long calls
(PLAN.md §4) — the signature accepts optional script content and can be
implemented as a streaming/chunked call without changing the core contract.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict

from app.core.domain import Transcript


class AnalysisResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    summary: str
    kpi_json: dict[str, Any]


@runtime_checkable
class Analyzer(Protocol):
    """LLM-based transcript analyzer — baseline or script-based mode."""

    def analyze(
        self,
        transcript: Transcript,
        script: str | None = None,
    ) -> AnalysisResult:
        """Analyze transcript and return summary + KPI scores."""
        ...
