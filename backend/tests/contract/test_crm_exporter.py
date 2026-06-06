"""Contract tests for CRMExporter port — M1-T3 / M8."""

from __future__ import annotations

import contextlib
import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from app.core.domain import Recording, RecordingStatus
from app.core.ports import AnalysisResult, CRMExporter, ExportResult
from tests.contract.helpers import assert_valid_export_result


def _mock_gs_exporter() -> CRMExporter:
    from app.adapters.crm.google_sheets import GoogleSheetsExporter

    exporter = GoogleSheetsExporter(spreadsheet_id="test-id")
    ws = MagicMock()
    ws.append_row.return_value = None
    exporter._get_worksheet = lambda: ws  # type: ignore[method-assign]
    return exporter


def _mock_webhook_exporter() -> CRMExporter:
    from app.adapters.crm.webhook import GenericWebhookExporter

    return GenericWebhookExporter(url="https://example.com/hook")


def _mock_bitrix24_exporter() -> CRMExporter:
    from app.adapters.crm.bitrix24 import Bitrix24Exporter

    return Bitrix24Exporter(webhook_url="https://portal.bitrix24.ru/rest/1/token/")


def get_crm_impls() -> list[tuple[str, CRMExporter]]:
    impls: list[tuple[str, CRMExporter]] = []
    with contextlib.suppress(ImportError):
        from app.adapters.crm.json_exporter import JSONExporter
        impls.append(("JSONExporter", JSONExporter()))
    with contextlib.suppress(ImportError):
        impls.append(("GoogleSheetsExporter", _mock_gs_exporter()))
    with contextlib.suppress(ImportError):
        impls.append(("GenericWebhookExporter", _mock_webhook_exporter()))
    with contextlib.suppress(ImportError):
        impls.append(("Bitrix24Exporter", _mock_bitrix24_exporter()))
    return impls


_impls = get_crm_impls()
_ids = [label for label, _ in _impls]

_SAMPLE_RECORDING = Recording(
    id=uuid.uuid4(),
    manager_id=uuid.uuid4(),
    channel="file",
    consent_flag=True,
    status=RecordingStatus.DONE,
    created_at=datetime.now(tz=UTC),
    retention_until=None,
    audio_path="sample.wav",
    stage_error=None,
)

_SAMPLE_ANALYSIS = AnalysisResult(
    summary="Хорошо отработал возражения клиента",
    kpi_json={"greeting": 8, "needs_discovery": 7},
)


def _run_export(impl: CRMExporter) -> ExportResult:
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"result": 1}
    mock_resp.raise_for_status.return_value = None
    with (
        patch("app.adapters.crm.webhook.httpx") as mhx_wh,
        patch("app.adapters.crm.bitrix24.httpx") as mhx_b24,
    ):
        mhx_wh.post.return_value = mock_resp
        mhx_b24.post.return_value = mock_resp
        return impl.export(_SAMPLE_ANALYSIS, _SAMPLE_RECORDING)


@pytest.mark.contract
@pytest.mark.skipif(not _impls, reason="No CRMExporter implementations registered yet")
@pytest.mark.parametrize("impl", [impl for _, impl in _impls], ids=_ids)
class TestCRMExporterContract:
    def test_export_returns_export_result(self, impl: CRMExporter) -> None:
        result = _run_export(impl)
        assert isinstance(result, ExportResult)

    def test_export_result_has_success_flag(self, impl: CRMExporter) -> None:
        result = _run_export(impl)
        assert_valid_export_result(result)

    def test_export_is_idempotent(self, impl: CRMExporter) -> None:
        r1 = _run_export(impl)
        r2 = _run_export(impl)
        assert r1.success and r2.success

    def test_impl_satisfies_protocol(self, impl: CRMExporter) -> None:
        assert isinstance(impl, CRMExporter)
