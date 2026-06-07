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


def applicable_kpis(cfg: KpiConfig, include_script: bool) -> list[Any]:
    """Return KPIs the LLM is asked to score for this call.

    Baseline mode (no script): script-only KPIs are excluded — the prompt does
    not ask for them, so they must not be required by the schema either.
    """
    return [
        kpi for kpi in cfg.kpis
        if kpi.applies_to != "script" or include_script
    ]


def build_kpi_result_model(
    cfg: KpiConfig, include_script: bool = False
) -> type[BaseModel]:
    """Build a Pydantic model with one field per applicable KPI.

    Only KPIs that the prompt actually requests are made required, so baseline
    analysis (no script assigned) does not fail on missing `script_compliance`.
    """
    fields: dict[str, Any] = {
        kpi.id: (KpiEntry, Field(..., description=kpi.label))
        for kpi in applicable_kpis(cfg, include_script)
    }
    return create_model("KpiResult", **fields)
