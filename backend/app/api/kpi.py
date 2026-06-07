"""GET /api/kpi — KPI rubric config for the UI (labels, type, weight).

Single source of truth is kpi.yaml; the frontend uses this to render the
analysis card as a human-readable checklist instead of raw KPI ids.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.deps import AnyUserRequired
from app.config.kpi import load_kpi_config

router = APIRouter(prefix="/api/kpi", tags=["kpi"])


class KpiItemOut(BaseModel):
    id: str
    label: str
    type: str
    weight: float
    applies_to: str
    include_in_score: bool


@router.get("", response_model=list[KpiItemOut], dependencies=[AnyUserRequired])
async def list_kpis() -> list[KpiItemOut]:
    """Return the KPI rubric (id, label, type, weight, applies_to)."""
    cfg = load_kpi_config()
    return [
        KpiItemOut(
            id=k.id,
            label=k.label,
            type=k.type,
            weight=k.weight,
            applies_to=k.applies_to,
            include_in_score=k.include_in_score,
        )
        for k in cfg.kpis
    ]
