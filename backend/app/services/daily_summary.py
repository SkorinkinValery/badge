"""Daily summary aggregation service — M6-T4."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.kpi import KpiConfig, load_kpi_config
from app.db.models.analysis import AnalysisModel
from app.db.models.recording import RecordingModel

# A KPI is flagged as a problem area when its average score is below this bar
# (0-10 scale; for fact-KPIs the value is 10 when fulfilled, 0 otherwise).
_PROBLEM_BELOW = 7.0


@dataclass
class KpiStat:
    kpi_id: str
    label: str
    kpi_type: str  # "scale" | "fact"
    avg_value: float  # mean KPI score across the day's calls (0-10)
    fulfilled_pct: float  # % of calls meeting the bar (kept for reference)


@dataclass
class DailySummary:
    manager_id: uuid.UUID
    date: date
    total_recordings: int
    total_duration_s: float
    avg_duration_s: float
    avg_score: float | None
    kpi_stats: list[KpiStat] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)
    top_issues: list[str] = field(default_factory=list)


def _extract_value(raw: Any) -> float | None:
    """Extract numeric value from kpi_json entry (dict or plain number)."""
    if isinstance(raw, dict):
        v = raw.get("value")
        return float(v) if v is not None else None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def aggregate_summary(
    recordings: list[Any],
    analyses: list[Any],
    manager_id: uuid.UUID,
    target_date: date,
) -> DailySummary:
    """Aggregate summary without KPI breakdown (no config needed)."""
    return aggregate_summary_with_kpi(
        recordings, analyses, manager_id, target_date, kpi_cfg=None
    )


def aggregate_summary_with_kpi(
    recordings: list[Any],
    analyses: list[Any],
    manager_id: uuid.UUID,
    target_date: date,
    kpi_cfg: KpiConfig | None = None,
) -> DailySummary:
    """Aggregate summary with optional KPI breakdown."""
    total = len(recordings)
    if total == 0:
        return DailySummary(
            manager_id=manager_id,
            date=target_date,
            total_recordings=0,
            total_duration_s=0.0,
            avg_duration_s=0.0,
            avg_score=None,
        )

    total_dur = sum(
        r.duration_seconds for r in recordings if r.duration_seconds is not None
    )
    avg_dur = total_dur / total if total else 0.0

    ana_by_rec: dict[uuid.UUID, Any] = {a.recording_id: a for a in analyses}

    scores = [
        a.score
        for a in analyses
        if a.score is not None
    ]
    avg_score: float | None = (sum(scores) / len(scores)) if scores else None

    if kpi_cfg is None:
        return DailySummary(
            manager_id=manager_id,
            date=target_date,
            total_recordings=total,
            total_duration_s=total_dur,
            avg_duration_s=avg_dur,
            avg_score=avg_score,
        )

    kpi_fulfilled: dict[str, int] = {kpi.id: 0 for kpi in kpi_cfg.kpis}
    kpi_total: dict[str, int] = {kpi.id: 0 for kpi in kpi_cfg.kpis}
    kpi_sum: dict[str, float] = {kpi.id: 0.0 for kpi in kpi_cfg.kpis}

    violations_set: set[str] = set()
    kpi_by_id = {k.id: k for k in kpi_cfg.kpis}

    for rec in recordings:
        ana = ana_by_rec.get(rec.id)
        if ana is None or not ana.kpi_json:
            continue
        kpi_json: dict[str, Any] = ana.kpi_json
        for kpi_id, kpi_item in kpi_by_id.items():
            raw = kpi_json.get(kpi_id)
            if raw is None:
                continue
            val = _extract_value(raw)
            if val is None:
                continue
            kpi_total[kpi_id] += 1
            kpi_sum[kpi_id] += val
            if kpi_item.type == "fact":
                if val >= 10.0:
                    kpi_fulfilled[kpi_id] += 1
                else:
                    violations_set.add(kpi_item.label)
            else:
                if val >= 5.0:
                    kpi_fulfilled[kpi_id] += 1

    stats: list[KpiStat] = []
    for kpi_item in kpi_cfg.kpis:
        tot = kpi_total[kpi_item.id]
        if tot == 0:
            continue
        stats.append(
            KpiStat(
                kpi_id=kpi_item.id,
                label=kpi_item.label,
                kpi_type=kpi_item.type,
                avg_value=kpi_sum[kpi_item.id] / tot,
                fulfilled_pct=kpi_fulfilled[kpi_item.id] / tot * 100.0,
            )
        )

    # Problem areas = weakest KPIs (lowest average score) below the "good" bar.
    issues_sorted = sorted(
        (s for s in stats if s.avg_value < _PROBLEM_BELOW), key=lambda s: s.avg_value
    )
    top_issues = [s.label for s in issues_sorted[:3]]

    return DailySummary(
        manager_id=manager_id,
        date=target_date,
        total_recordings=total,
        total_duration_s=total_dur,
        avg_duration_s=avg_dur,
        avg_score=avg_score,
        kpi_stats=stats,
        violations=sorted(violations_set),
        top_issues=top_issues,
    )


async def compute_daily_summary(
    manager_id: uuid.UUID,
    target_date: date,
    session: AsyncSession,
) -> DailySummary:
    """Fetch recordings + analyses for manager on date, return aggregated summary."""
    from datetime import UTC, datetime

    day_start = datetime(
        target_date.year, target_date.month, target_date.day, tzinfo=UTC
    )
    day_end = datetime(
        target_date.year, target_date.month, target_date.day, 23, 59, 59, tzinfo=UTC
    )

    rec_result = await session.execute(
        select(RecordingModel)
        .where(RecordingModel.manager_id == manager_id)
        .where(RecordingModel.created_at >= day_start)
        .where(RecordingModel.created_at <= day_end)
    )
    recordings = list(rec_result.scalars().all())

    if not recordings:
        return DailySummary(
            manager_id=manager_id,
            date=target_date,
            total_recordings=0,
            total_duration_s=0.0,
            avg_duration_s=0.0,
            avg_score=None,
        )

    rec_ids = [r.id for r in recordings]
    ana_result = await session.execute(
        select(AnalysisModel).where(AnalysisModel.recording_id.in_(rec_ids))
    )
    analyses = list(ana_result.scalars().all())

    kpi_cfg = load_kpi_config()
    return aggregate_summary_with_kpi(recordings, analyses, manager_id, target_date, kpi_cfg)
