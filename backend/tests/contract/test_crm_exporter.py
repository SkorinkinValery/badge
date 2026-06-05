"""Contract tests for CRMExporter port — M1-T3."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.core.domain import Recording, RecordingStatus
from app.core.ports import AnalysisResult, CRMExporter, ExportResult
from tests.contract.helpers import assert_valid_export_result


def get_crm_impls() -> list[tuple[str, CRMExporter]]:
    try:
        from app.adapters.crm.json_exporter import JSONExporter
        return [("JSONExporter", JSONExporter())]
    except ImportError:
        return []


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


@pytest.mark.contract
@pytest.mark.skipif(not _impls, reason="No CRMExporter implementations registered yet")
@pytest.mark.parametrize("impl", [impl for _, impl in _impls], ids=_ids)
class TestCRMExporterContract:
    def test_export_returns_export_result(self, impl: CRMExporter) -> None:
        result = impl.export(_SAMPLE_ANALYSIS, _SAMPLE_RECORDING)
        assert isinstance(result, ExportResult)

    def test_export_result_has_success_flag(self, impl: CRMExporter) -> None:
        result = impl.export(_SAMPLE_ANALYSIS, _SAMPLE_RECORDING)
        assert_valid_export_result(result)

    def test_export_is_idempotent(self, impl: CRMExporter) -> None:
        """Exporting the same data twice should both succeed without error."""
        r1 = impl.export(_SAMPLE_ANALYSIS, _SAMPLE_RECORDING)
        r2 = impl.export(_SAMPLE_ANALYSIS, _SAMPLE_RECORDING)
        assert r1.success and r2.success

    def test_impl_satisfies_protocol(self, impl: CRMExporter) -> None:
        assert isinstance(impl, CRMExporter)
