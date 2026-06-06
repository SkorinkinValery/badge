"""Bitrix24Exporter — sends analysis result to Bitrix24 via REST webhook (M8-T5).

Webhook URL comes from config (never hardcoded).
Optional field_mapping remaps payload keys to Bitrix24 entity fields.
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
_DEFAULT_METHOD = "crm.deal.add.json"


class Bitrix24Exporter:
    """Posts analysis result to a Bitrix24 REST webhook.

    webhook_url: full webhook base URL, e.g. https://portal.bitrix24.ru/rest/1/<token>/
    field_mapping: {bitrix_field: payload_key} — overrides default full-payload POST
    """

    def __init__(
        self,
        webhook_url: str,
        field_mapping: dict[str, str] | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
        score: float | None = None,
        verdict: str | None = None,
    ) -> None:
        self._webhook_url = webhook_url.rstrip("/") + "/"
        self._field_mapping = field_mapping
        self._timeout = timeout
        self._score = score
        self._verdict = verdict

    def _build_body(self, payload: dict) -> dict:  # type: ignore[type-arg]
        if not self._field_mapping:
            return {"fields": payload}
        return {
            "fields": {
                b24_field: payload.get(payload_key, "")
                for b24_field, payload_key in self._field_mapping.items()
            }
        }

    def export(self, analysis: AnalysisResult, recording: Recording) -> ExportResult:
        payload = build_export_payload(
            analysis, recording, score=self._score, verdict=self._verdict
        )
        url = self._webhook_url + _DEFAULT_METHOD
        body = self._build_body(payload)
        try:
            resp = httpx.post(url, json=body, timeout=self._timeout)
            resp.raise_for_status()
            result_id = resp.json().get("result")
            external_id = str(result_id) if result_id is not None else payload["recording_id"]
            log.info(
                "bitrix24.exported",
                recording_id=payload["recording_id"],
                external_id=external_id,
            )
            return ExportResult(success=True, external_id=external_id)
        except Exception as exc:
            log.error("bitrix24.export_failed", webhook_url=self._webhook_url, error=str(exc))
            return ExportResult(success=False, error=str(exc))
