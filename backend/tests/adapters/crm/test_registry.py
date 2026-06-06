"""Unit tests for M8-T3: CRM exporter registry."""

from __future__ import annotations

import pytest


class TestCrmRegistry:
    def test_json_resolves(self) -> None:
        from app.adapters.crm.json_exporter import JSONExporter
        from app.adapters.crm.registry import get_exporter

        exporter = get_exporter("json", {})
        assert isinstance(exporter, JSONExporter)

    def test_google_sheets_resolves(self) -> None:
        from app.adapters.crm.google_sheets import GoogleSheetsExporter
        from app.adapters.crm.registry import get_exporter

        cfg = {"spreadsheet_id": "test-id", "worksheet_name": "Sheet1"}
        exporter = get_exporter("google_sheets", cfg)
        assert isinstance(exporter, GoogleSheetsExporter)

    def test_webhook_resolves(self) -> None:
        from app.adapters.crm.registry import get_exporter
        from app.adapters.crm.webhook import GenericWebhookExporter

        cfg = {"url": "https://example.com/hook"}
        exporter = get_exporter("webhook", cfg)
        assert isinstance(exporter, GenericWebhookExporter)

    def test_bitrix24_resolves(self) -> None:
        from app.adapters.crm.bitrix24 import Bitrix24Exporter
        from app.adapters.crm.registry import get_exporter

        cfg = {"webhook_url": "https://portal.bitrix24.ru/rest/1/token/"}
        exporter = get_exporter("bitrix24", cfg)
        assert isinstance(exporter, Bitrix24Exporter)

    def test_unknown_provider_raises(self) -> None:
        from app.adapters.crm.registry import UnknownCrmProviderError, get_exporter

        with pytest.raises(UnknownCrmProviderError):
            get_exporter("unknown_crm", {})

    def test_switching_provider_changes_adapter(self) -> None:
        from app.adapters.crm.json_exporter import JSONExporter
        from app.adapters.crm.registry import get_exporter
        from app.adapters.crm.webhook import GenericWebhookExporter

        j = get_exporter("json", {})
        w = get_exporter("webhook", {"url": "https://x.com"})
        assert isinstance(j, JSONExporter)
        assert isinstance(w, GenericWebhookExporter)
        assert type(j) is not type(w)

    def test_available_providers_list(self) -> None:
        from app.adapters.crm.registry import AVAILABLE_PROVIDERS

        assert "json" in AVAILABLE_PROVIDERS
        assert "google_sheets" in AVAILABLE_PROVIDERS
        assert "webhook" in AVAILABLE_PROVIDERS
        assert "bitrix24" in AVAILABLE_PROVIDERS
