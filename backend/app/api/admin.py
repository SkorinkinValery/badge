"""Admin API — daily summary — M6-T4."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AnyUserRequired
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


@router.get("/summary", response_model=DailySummaryOut, dependencies=[AnyUserRequired])
async def get_daily_summary(
    manager_id: uuid.UUID,
    date: date,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DailySummaryOut:
    summary = await compute_daily_summary(manager_id, date, session)
    return _to_out(summary)
