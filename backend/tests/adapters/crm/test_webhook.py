"""Contract tests for M8-T4: GenericWebhookExporter (HTTP mocked)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import patch, MagicMock

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
    summary="Тест вебхука",
    kpi_json={"greeting": 8},
)


def _make_exporter() -> object:
    from app.adapters.crm.webhook import GenericWebhookExporter

    return GenericWebhookExporter(url="https://example.com/hook")


@pytest.fixture
def mock_http_200():  # type: ignore[no-untyped-def]
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status.return_value = None
    with patch("app.adapters.crm.webhook.httpx") as mock_httpx:
        mock_httpx.post.return_value = mock_resp
        yield mock_httpx


@pytest.fixture
def mock_http_500():  # type: ignore[no-untyped-def]
    import httpx
    with patch("app.adapters.crm.webhook.httpx") as mock_httpx:
        mock_httpx.post.side_effect = httpx.HTTPError("Server error")
        yield mock_httpx


class TestGenericWebhookExporter:
    def test_satisfies_crm_exporter_protocol(self) -> None:
        exporter = _make_exporter()
        assert isinstance(exporter, CRMExporter)

    def test_export_returns_export_result(self, mock_http_200: object) -> None:
        exporter = _make_exporter()
        result = exporter.export(_SAMPLE_ANALYSIS, _SAMPLE_RECORDING)  # type: ignore[arg-type]
        assert isinstance(result, ExportResult)

    def test_export_success_on_2xx(self, mock_http_200: object) -> None:
        exporter = _make_exporter()
        result = exporter.export(_SAMPLE_ANALYSIS, _SAMPLE_RECORDING)  # type: ignore[arg-type]
        assert result.success is True

    def test_export_posts_to_url(self, mock_http_200: object) -> None:
        import httpx
        with patch("app.adapters.crm.webhook.httpx") as mock_hx:
            mock_resp = MagicMock()
            mock_resp.raise_for_status.return_value = None
            mock_hx.post.return_value = mock_resp
            exporter = _make_exporter()
            exporter.export(_SAMPLE_ANALYSIS, _SAMPLE_RECORDING)  # type: ignore[arg-type]
            mock_hx.post.assert_called_once()
            call_args = mock_hx.post.call_args
            assert "https://example.com/hook" in str(call_args)

    def test_export_payload_contains_recording_id(self, mock_http_200: object) -> None:
        import httpx
        with patch("app.adapters.crm.webhook.httpx") as mock_hx:
            mock_resp = MagicMock()
            mock_resp.raise_for_status.return_value = None
            mock_hx.post.return_value = mock_resp
            exporter = _make_exporter()
            exporter.export(_SAMPLE_ANALYSIS, _SAMPLE_RECORDING)  # type: ignore[arg-type]
            call_kwargs = mock_hx.post.call_args
            # json param should contain recording_id
            json_data = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json", {})
            assert str(_SAMPLE_RECORDING.id) in str(json_data)

    def test_export_fails_on_http_error(self, mock_http_500: object) -> None:
        exporter = _make_exporter()
        result = exporter.export(_SAMPLE_ANALYSIS, _SAMPLE_RECORDING)  # type: ignore[arg-type]
        assert result.success is False
        assert result.error is not None

    def test_extra_headers_from_config(self) -> None:
        from app.adapters.crm.webhook import GenericWebhookExporter
        import httpx

        with patch("app.adapters.crm.webhook.httpx") as mock_hx:
            mock_resp = MagicMock()
            mock_resp.raise_for_status.return_value = None
            mock_hx.post.return_value = mock_resp
            exporter = GenericWebhookExporter(
                url="https://example.com/hook",
                headers={"X-Secret": "abc"},
            )
            exporter.export(_SAMPLE_ANALYSIS, _SAMPLE_RECORDING)  # type: ignore[arg-type]
            call_kwargs = mock_hx.post.call_args
            headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers", {})
            assert "X-Secret" in headers
