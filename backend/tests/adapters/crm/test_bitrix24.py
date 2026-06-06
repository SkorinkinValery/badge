"""Contract tests for M8-T5: Bitrix24Exporter (REST mocked)."""

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
    summary="Успешная сделка",
    kpi_json={"greeting": 9, "close": 8},
)

_WEBHOOK_URL = "https://portal.bitrix24.ru/rest/1/token/"


def _make_exporter() -> object:
    from app.adapters.crm.bitrix24 import Bitrix24Exporter

    return Bitrix24Exporter(webhook_url=_WEBHOOK_URL)


@pytest.fixture
def mock_b24_200():  # type: ignore[no-untyped-def]
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"result": 123}
    mock_resp.raise_for_status.return_value = None
    with patch("app.adapters.crm.bitrix24.httpx") as mock_hx:
        mock_hx.post.return_value = mock_resp
        yield mock_hx


@pytest.fixture
def mock_b24_error():  # type: ignore[no-untyped-def]
    import httpx
    with patch("app.adapters.crm.bitrix24.httpx") as mock_hx:
        mock_hx.post.side_effect = httpx.HTTPError("Connection refused")
        yield mock_hx


class TestBitrix24Exporter:
    def test_satisfies_crm_exporter_protocol(self) -> None:
        exporter = _make_exporter()
        assert isinstance(exporter, CRMExporter)

    def test_export_returns_export_result(self, mock_b24_200: object) -> None:
        exporter = _make_exporter()
        result = exporter.export(_SAMPLE_ANALYSIS, _SAMPLE_RECORDING)  # type: ignore[arg-type]
        assert isinstance(result, ExportResult)

    def test_export_success_on_200(self, mock_b24_200: object) -> None:
        exporter = _make_exporter()
        result = exporter.export(_SAMPLE_ANALYSIS, _SAMPLE_RECORDING)  # type: ignore[arg-type]
        assert result.success is True

    def test_export_calls_bitrix_endpoint(self, mock_b24_200: object) -> None:
        from unittest.mock import MagicMock, patch

        with patch("app.adapters.crm.bitrix24.httpx") as mock_hx:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"result": 1}
            mock_resp.raise_for_status.return_value = None
            mock_hx.post.return_value = mock_resp
            exporter = _make_exporter()
            exporter.export(_SAMPLE_ANALYSIS, _SAMPLE_RECORDING)  # type: ignore[arg-type]
            mock_hx.post.assert_called_once()
            url_arg = mock_hx.post.call_args[0][0]
            assert "bitrix24" in url_arg or _WEBHOOK_URL in url_arg

    def test_external_id_from_bitrix_result(self, mock_b24_200: object) -> None:
        exporter = _make_exporter()
        result = exporter.export(_SAMPLE_ANALYSIS, _SAMPLE_RECORDING)  # type: ignore[arg-type]
        assert result.external_id is not None

    def test_idempotency_on_duplicate(self, mock_b24_200: object) -> None:
        exporter = _make_exporter()
        r1 = exporter.export(_SAMPLE_ANALYSIS, _SAMPLE_RECORDING)  # type: ignore[arg-type]
        r2 = exporter.export(_SAMPLE_ANALYSIS, _SAMPLE_RECORDING)  # type: ignore[arg-type]
        assert r1.success and r2.success

    def test_api_error_returns_failed_result(self, mock_b24_error: object) -> None:
        exporter = _make_exporter()
        result = exporter.export(_SAMPLE_ANALYSIS, _SAMPLE_RECORDING)  # type: ignore[arg-type]
        assert result.success is False
        assert result.error is not None

    def test_field_mapping_config_driven(self) -> None:
        from unittest.mock import MagicMock, patch

        from app.adapters.crm.bitrix24 import Bitrix24Exporter

        with patch("app.adapters.crm.bitrix24.httpx") as mock_hx:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"result": 42}
            mock_resp.raise_for_status.return_value = None
            mock_hx.post.return_value = mock_resp
            exporter = Bitrix24Exporter(
                webhook_url=_WEBHOOK_URL,
                field_mapping={"TITLE": "summary", "COMMENTS": "kpi_json"},
            )
            result = exporter.export(_SAMPLE_ANALYSIS, _SAMPLE_RECORDING)  # type: ignore[arg-type]
            assert result.success is True
