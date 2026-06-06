"""Admin API — daily summary (M6-T4), CRM settings (M8-T6)."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.crm.registry import AVAILABLE_PROVIDERS
from app.api.deps import AdminRequired, AnyUserRequired
from app.db.session import get_session
from app.services.daily_summary import DailySummary, compute_daily_summary

router = APIRouter(prefix="/api/admin", tags=["admin"])


class KpiStatOut(BaseModel):
    kpi_id: str
    label: str
    fulfilled_pct: float


class DailySummaryOut(BaseModel):
    manager_id: uuid.UUID
    date: date
    total_recordings: int
    total_duration_s: float
    avg_duration_s: float
    avg_score: float | None
    kpi_stats: list[KpiStatOut]
    violations: list[str]
    top_issues: list[str]


def _to_out(s: DailySummary) -> DailySummaryOut:
    return DailySummaryOut(
        manager_id=s.manager_id,
        date=s.date,
        total_recordings=s.total_recordings,
        total_duration_s=s.total_duration_s,
        avg_duration_s=s.avg_duration_s,
        avg_score=s.avg_score,
        kpi_stats=[
            KpiStatOut(kpi_id=k.kpi_id, label=k.label, fulfilled_pct=k.fulfilled_pct)
            for k in s.kpi_stats
        ],
        violations=s.violations,
        top_issues=s.top_issues,
    )


class CrmSettingsOut(BaseModel):
    active_crm: str
    available_providers: list[str]
    params: dict[str, Any]


class CrmSettingsIn(BaseModel):
    active_crm: str
    params: dict[str, Any] = {}


@router.get("/settings", response_model=CrmSettingsOut, dependencies=[AdminRequired])
async def get_crm_settings(request: Request) -> CrmSettingsOut:
    cfg: dict[str, Any] = request.app.state.crm_config
    return CrmSettingsOut(
        active_crm=cfg.get("active_crm", "json"),
        available_providers=sorted(AVAILABLE_PROVIDERS),
        params=cfg.get("params") or {},
    )


@router.put("/settings", response_model=CrmSettingsOut, dependencies=[AdminRequired])
async def put_crm_settings(body: CrmSettingsIn, request: Request) -> CrmSettingsOut:
    if body.active_crm not in AVAILABLE_PROVIDERS:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown CRM provider: {body.active_crm!r}. Available: {sorted(AVAILABLE_PROVIDERS)}",
        )
    request.app.state.crm_config = {
        "active_crm": body.active_crm,
        "params": body.params,
    }
    return CrmSettingsOut(
        active_crm=body.active_crm,
        available_providers=sorted(AVAILABLE_PROVIDERS),
        params=body.params,
    )


@router.get("/summary", response_model=DailySummaryOut, dependencies=[AnyUserRequired])
async def get_daily_summary(
    manager_id: uuid.UUID,
    date: date,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DailySummaryOut:
    summary = await compute_daily_summary(manager_id, date, session)
    return _to_out(summary)
