"""GoogleSheetsExporter — MVP default CRM adapter (M8-T2).

Appends one row per analysis to a Google Sheets spreadsheet.
Credentials come from env/config (service account JSON), never from code.
"""

from __future__ import annotations

import json
from typing import Any

import gspread
import gspread.utils
import structlog

from app.adapters.crm.payload import build_export_payload
from app.core.domain import Recording
from app.core.ports.analyzer import AnalysisResult
from app.core.ports.crm_exporter import ExportResult

log = structlog.get_logger(__name__)

# Ordered column headers — matches the row values list
_COLUMNS = [
    "recording_id",
    "manager_id",
    "channel",
    "created_at",
    "summary",
    "score",
    "verdict",
    "kpi_json",
]


class GoogleSheetsExporter:
    """Appends analysis results to a Google Sheets worksheet.

    credentials_json: parsed service account dict (None → uses env / ADC fallback).
    """

    def __init__(
        self,
        spreadsheet_id: str,
        worksheet_name: str = "Результаты",
        credentials_json: dict[str, Any] | None = None,
        score: float | None = None,
        verdict: str | None = None,
    ) -> None:
        self._spreadsheet_id = spreadsheet_id
        self._worksheet_name = worksheet_name
        self._credentials_json = credentials_json
        self._score = score
        self._verdict = verdict

    def _get_worksheet(self) -> gspread.Worksheet:
        if self._credentials_json:
            client = gspread.service_account_from_dict(self._credentials_json)
        else:
            client = gspread.service_account()
        spreadsheet = client.open_by_key(self._spreadsheet_id)
        return spreadsheet.worksheet(self._worksheet_name)

    def export(self, analysis: AnalysisResult, recording: Recording) -> ExportResult:
        payload = build_export_payload(
            analysis, recording, score=self._score, verdict=self._verdict
        )
        row = [
            str(payload.get("recording_id", "")),
            str(payload.get("manager_id", "")),
            str(payload.get("channel", "")),
            str(payload.get("created_at", "")),
            str(payload.get("summary", "")),
            str(payload.get("score", "") or ""),
            str(payload.get("verdict", "") or ""),
            json.dumps(payload.get("kpi_json") or {}, ensure_ascii=False),
        ]
        try:
            ws = self._get_worksheet()
            ws.append_row(row, value_input_option=gspread.utils.ValueInputOption.user_entered)
            log.info(
                "google_sheets.exported",
                recording_id=payload["recording_id"],
                spreadsheet_id=self._spreadsheet_id,
            )
            return ExportResult(success=True, external_id=payload["recording_id"])
        except Exception as exc:
            log.error("google_sheets.export_failed", error=str(exc))
            return ExportResult(success=False, error=str(exc))
