"""CRM exporter registry — resolves provider name + config → CRMExporter (M8-T3).

Provider is selected by active_crm in providers.yaml (or any config dict).
"""

from __future__ import annotations

from typing import Any

from app.core.ports.crm_exporter import CRMExporter

AVAILABLE_PROVIDERS: frozenset[str] = frozenset(
    {"json", "google_sheets", "webhook", "bitrix24"}
)


class UnknownCrmProviderError(ValueError):
    """Raised when the requested CRM provider name is not registered."""


def get_exporter(name: str, cfg: dict[str, Any]) -> CRMExporter:
    """Return a CRMExporter instance for *name* configured via *cfg*."""
    if name not in AVAILABLE_PROVIDERS:
        raise UnknownCrmProviderError(
            f"Unknown CRM provider: {name!r}. Available: {sorted(AVAILABLE_PROVIDERS)}"
        )
    if name == "json":
        from app.adapters.crm.json_exporter import JSONExporter

        return JSONExporter()

    if name == "google_sheets":
        from app.adapters.crm.google_sheets import GoogleSheetsExporter

        return GoogleSheetsExporter(
            spreadsheet_id=cfg["spreadsheet_id"],
            worksheet_name=cfg.get("worksheet_name", "Результаты"),
            credentials_json=cfg.get("credentials_json"),
        )

    if name == "webhook":
        from app.adapters.crm.webhook import GenericWebhookExporter

        return GenericWebhookExporter(
            url=cfg["url"],
            headers=cfg.get("headers"),
            timeout=float(cfg.get("timeout", 10.0)),
        )

    if name == "bitrix24":
        from app.adapters.crm.bitrix24 import Bitrix24Exporter

        return Bitrix24Exporter(
            webhook_url=cfg["webhook_url"],
            field_mapping=cfg.get("field_mapping"),
            timeout=float(cfg.get("timeout", 10.0)),
        )

    raise UnknownCrmProviderError(name)  # unreachable, satisfies mypy
