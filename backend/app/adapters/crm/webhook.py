"""GenericWebhookExporter — sends export payload as JSON POST (M8-T4).

Any HTTP endpoint can receive analysis results via this adapter.
URL and optional auth headers come from config.
"""

from __future__ import annotations

import httpx
import structlog

from app.adapters.crm.payload import build_export_payload
from app.core.domain import Recording
from app.core.ports.analyzer import AnalysisResult
from app.core.ports.crm_exporter import ExportResult

log = structlog.get_logger(__name__)

_DEFAULT_TIMEOUT = 10.0


class GenericWebhookExporter:
    """Posts analysis payload to a configurable webhook URL."""

    def __init__(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
        score: float | None = None,
        verdict: str | None = None,
    ) -> None:
        self._url = url
        self._headers = headers or {}
        self._timeout = timeout
        self._score = score
        self._verdict = verdict

    def export(self, analysis: AnalysisResult, recording: Recording) -> ExportResult:
        payload = build_export_payload(
            analysis, recording, score=self._score, verdict=self._verdict
        )
        try:
            resp = httpx.post(
                self._url,
                json=payload,
                headers=self._headers,
                timeout=self._timeout,
            )
            resp.raise_for_status()
            log.info(
                "webhook.exported",
                url=self._url,
                recording_id=payload["recording_id"],
                status=resp.status_code,
            )
            return ExportResult(success=True, external_id=payload["recording_id"])
        except Exception as exc:
            log.error("webhook.export_failed", url=self._url, error=str(exc))
            return ExportResult(success=False, error=str(exc))
