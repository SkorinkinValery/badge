"""JSONExporter — minimal CRM exporter that returns a JSON payload in-memory.

Used for the end-to-end pipeline in M4 and as a stub CRM for testing.
"""

from __future__ import annotations

import json
import uuid

from app.core.domain.recording import Recording
from app.core.ports.analyzer import AnalysisResult
from app.core.ports.crm_exporter import ExportResult


class JSONExporter:
    """Serialises analysis + recording to JSON; satisfies CRMExporter protocol."""

    def export(self, analysis: AnalysisResult, recording: Recording) -> ExportResult:
        payload = {
            "recording_id": str(recording.id),
            "manager_id": str(recording.manager_id),
            "channel": recording.channel,
            "summary": analysis.summary,
            "kpi_json": analysis.kpi_json,
        }
        export_id = str(uuid.uuid4())
        _ = json.dumps(payload)  # validate serialisability
        return ExportResult(success=True, external_id=export_id)
