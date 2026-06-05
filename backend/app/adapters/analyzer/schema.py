"""Dynamic KpiResult schema built from kpi.yaml — M4-T1.

One schema for all LLM providers (response_format / guided_json).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, create_model, field_validator

from app.config.kpi import KpiConfig


class KpiEntry(BaseModel):
    """Per-KPI structured LLM output: value + citation + reasoning."""

    kpi_type: str = "scale"
    value: float
    quote: str
    comment: str

    @field_validator("value")
    @classmethod
    def validate_value_range(cls, v: float, info: Any) -> float:
        kpi_type = (info.data or {}).get("kpi_type", "scale")
        if kpi_type == "fact" and v not in (0.0, 10.0):
            raise ValueError(f"fact KPI value must be 0 or 10, got {v}")
        if not (0.0 <= v <= 10.0):
            raise ValueError(f"KPI value must be in [0, 10], got {v}")
        return v


def build_kpi_result_model(cfg: KpiConfig) -> type[BaseModel]:
    """Build a Pydantic model with one field per KPI, validated against the config."""
    fields: dict[str, Any] = {
        kpi.id: (KpiEntry, Field(..., description=kpi.label))
        for kpi in cfg.kpis
    }
    return create_model("KpiResult", **fields)
