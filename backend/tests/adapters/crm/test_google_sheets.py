"""Contract tests for M8-T2: GoogleSheetsExporter (Google API mocked)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from app.core.domain import Recording, RecordingStatus
from app.core.ports import AnalysisResult, CRMExporter, ExportResult

_SAMPLE_RECORDING = Recording(
    id=uuid.uuid4(),
    manager_id=uuid.uuid4(),
    channel="file",
    consent_flag=True,
    status=RecordingStatus.DONE,
    created_at=datetime(2026, 6, 6, 10, 0, 0, tzinfo=UTC),
    retention_until=None,
    audio_path="sample.wav",
    stage_error=None,
)

_SAMPLE_ANALYSIS = AnalysisResult(
    summary="Менеджер успешно закрыл сделку",
    kpi_json={"greeting": 9, "needs_discovery": 8},
)


def _make_exporter() -> object:
    from app.adapters.crm.google_sheets import GoogleSheetsExporter

    return GoogleSheetsExporter(
        spreadsheet_id="test-spreadsheet-id",
        worksheet_name="Результаты",
        credentials_json=None,  # service account not needed in tests (API mocked)
    )


@pytest.fixture
def mock_gspread():  # type: ignore[no-untyped-def]
    """Patch gspread so no real Google API calls are made."""
    mock_ws = MagicMock()
    mock_ws.append_row.return_value = None
    mock_ws.get_all_values.return_value = []

    mock_spreadsheet = MagicMock()
    mock_spreadsheet.worksheet.return_value = mock_ws

    mock_client = MagicMock()
    mock_client.open_by_key.return_value = mock_spreadsheet

    with patch("app.adapters.crm.google_sheets.gspread") as mock_gs:
        mock_gs.service_account_from_dict.return_value = mock_client
        mock_gs.service_account.return_value = mock_client
        yield mock_client, mock_spreadsheet, mock_ws


class TestGoogleSheetsExporter:
    def test_satisfies_crm_exporter_protocol(self) -> None:
        exporter = _make_exporter()
        assert isinstance(exporter, CRMExporter)

    def test_export_returns_export_result(self, mock_gspread: tuple) -> None:
        exporter = _make_exporter()
        result = exporter.export(_SAMPLE_ANALYSIS, _SAMPLE_RECORDING)  # type: ignore[arg-type]
        assert isinstance(result, ExportResult)

    def test_export_success_true(self, mock_gspread: tuple) -> None:
        exporter = _make_exporter()
        result = exporter.export(_SAMPLE_ANALYSIS, _SAMPLE_RECORDING)  # type: ignore[arg-type]
        assert result.success is True

    def test_export_calls_append_row(self, mock_gspread: tuple) -> None:
        _, _, mock_ws = mock_gspread
        exporter = _make_exporter()
        exporter.export(_SAMPLE_ANALYSIS, _SAMPLE_RECORDING)  # type: ignore[arg-type]
        mock_ws.append_row.assert_called_once()

    def test_export_row_contains_recording_id(self, mock_gspread: tuple) -> None:
        _, _, mock_ws = mock_gspread
        exporter = _make_exporter()
        exporter.export(_SAMPLE_ANALYSIS, _SAMPLE_RECORDING)  # type: ignore[arg-type]
        args = mock_ws.append_row.call_args[0][0]
        assert str(_SAMPLE_RECORDING.id) in args

    def test_export_row_contains_summary(self, mock_gspread: tuple) -> None:
        _, _, mock_ws = mock_gspread
        exporter = _make_exporter()
        exporter.export(_SAMPLE_ANALYSIS, _SAMPLE_RECORDING)  # type: ignore[arg-type]
        args = mock_ws.append_row.call_args[0][0]
        assert _SAMPLE_ANALYSIS.summary in args

    def test_credentials_none_uses_anon_or_env(self, mock_gspread: tuple) -> None:
        """With credentials_json=None the exporter should not crash (test env)."""
        exporter = _make_exporter()
        result = exporter.export(_SAMPLE_ANALYSIS, _SAMPLE_RECORDING)  # type: ignore[arg-type]
        assert isinstance(result, ExportResult)

    def test_export_idempotent_on_duplicate(self, mock_gspread: tuple) -> None:
        """Calling export twice should both succeed (append-only idempotency)."""
        exporter = _make_exporter()
        r1 = exporter.export(_SAMPLE_ANALYSIS, _SAMPLE_RECORDING)  # type: ignore[arg-type]
        r2 = exporter.export(_SAMPLE_ANALYSIS, _SAMPLE_RECORDING)  # type: ignore[arg-type]
        assert r1.success and r2.success

    def test_api_error_returns_failed_result(self, mock_gspread: tuple) -> None:
        _, _, mock_ws = mock_gspread
        mock_ws.append_row.side_effect = Exception("Google API error")
        exporter = _make_exporter()
        result = exporter.export(_SAMPLE_ANALYSIS, _SAMPLE_RECORDING)  # type: ignore[arg-type]
        assert result.success is False
        assert result.error is not None
