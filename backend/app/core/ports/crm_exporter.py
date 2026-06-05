"""CRMExporter port and ExportResult DTO."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict

from app.core.domain import Recording
from app.core.ports.analyzer import AnalysisResult


class ExportResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    success: bool
    external_id: str | None = None
    error: str | None = None


@runtime_checkable
class CRMExporter(Protocol):
    """Exports analysis results to a CRM or other external system."""

    def export(self, analysis: AnalysisResult, recording: Recording) -> ExportResult:
        """Export analysis + recording metadata; return result with idempotency id."""
        ...
