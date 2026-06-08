"""Unit tests for daily_summary aggregation — M6-T4."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

import pytest


def _make_recording(
    manager_id: uuid.UUID,
    status: str = "done",
    duration: float | None = None,
    created_at: datetime | None = None,
) -> object:
    from unittest.mock import MagicMock

    from app.db.models.recording import RecordingModel

    rec = MagicMock(spec=RecordingModel)
    rec.id = uuid.uuid4()
    rec.manager_id = manager_id
    rec.status = status
    rec.duration_seconds = duration
    rec.created_at = created_at or datetime.now(tz=UTC)
    return rec


def _make_analysis(
    recording_id: uuid.UUID,
    score: float | None = None,
    kpi_json: dict | None = None,
    mode: str = "baseline",
) -> object:
    from unittest.mock import MagicMock

    from app.db.models.analysis import AnalysisModel

    a = MagicMock(spec=AnalysisModel)
    a.recording_id = recording_id
    a.score = score
    a.kpi_json = kpi_json or {}
    a.mode = mode
    return a


def test_empty_day_returns_zeros() -> None:
    from app.services.daily_summary import aggregate_summary

    manager_id = uuid.uuid4()
    result = aggregate_summary([], [], manager_id, date.today())

    assert result.total_recordings == 0
    assert result.total_duration_s == 0.0
    assert result.avg_duration_s == 0.0
    assert result.avg_score is None
    assert result.kpi_stats == []
    assert result.violations == []
    assert result.top_issues == []


def test_single_recording_correct_counts() -> None:
    from app.services.daily_summary import aggregate_summary

    manager_id = uuid.uuid4()
    rec = _make_recording(manager_id, status="done", duration=180.0)
    ana = _make_analysis(rec.id, score=75.0)  # type: ignore[union-attr]

    result = aggregate_summary([rec], [ana], manager_id, date.today())

    assert result.total_recordings == 1
    assert result.total_duration_s == 180.0
    assert result.avg_duration_s == 180.0
    assert result.avg_score == 75.0


def test_avg_score_ignores_recordings_without_analysis() -> None:
    from app.services.daily_summary import aggregate_summary

    manager_id = uuid.uuid4()
    rec1 = _make_recording(manager_id, duration=60.0)
    rec2 = _make_recording(manager_id, duration=120.0)
    ana1 = _make_analysis(rec1.id, score=80.0)  # type: ignore[union-attr]
    # rec2 has no analysis

    result = aggregate_summary([rec1, rec2], [ana1], manager_id, date.today())

    assert result.total_recordings == 2
    assert result.avg_score == 80.0


def test_violations_detected_for_fact_kpi_with_zero_value() -> None:
    from app.config.kpi import KpiConfig, KpiItem
    from app.services.daily_summary import aggregate_summary_with_kpi

    manager_id = uuid.uuid4()
    rec = _make_recording(manager_id)
    kpi_json = {
        "price_discussed": {"kpi_type": "fact", "value": 0.0, "quote": "", "comment": ""},
        "cta": {"kpi_type": "fact", "value": 10.0, "quote": "", "comment": ""},
    }
    ana = _make_analysis(rec.id, score=50.0, kpi_json=kpi_json)  # type: ignore[union-attr]

    kpi_cfg = KpiConfig(
        kpis=[
            KpiItem(
                id="price_discussed",
                label="Обсуждение цены",
                type="fact",
                weight=0.5,
                anchors=[],
                applies_to="baseline",
                include_in_score=True,
            ),
            KpiItem(
                id="cta",
                label="CTA",
                type="fact",
                weight=1.0,
                anchors=[],
                applies_to="baseline",
                include_in_score=True,
            ),
        ]
    )

    result = aggregate_summary_with_kpi([rec], [ana], manager_id, date.today(), kpi_cfg)

    assert "Обсуждение цены" in result.violations
    assert "CTA" not in result.violations


def test_kpi_stats_pct_for_fact_type() -> None:
    from app.config.kpi import KpiConfig, KpiItem
    from app.services.daily_summary import aggregate_summary_with_kpi

    manager_id = uuid.uuid4()
    rec1 = _make_recording(manager_id)
    rec2 = _make_recording(manager_id)

    kpi_json_pass = {"cta": {"kpi_type": "fact", "value": 10.0, "quote": "", "comment": ""}}
    kpi_json_fail = {"cta": {"kpi_type": "fact", "value": 0.0, "quote": "", "comment": ""}}

    ana1 = _make_analysis(rec1.id, score=90.0, kpi_json=kpi_json_pass)  # type: ignore[union-attr]
    ana2 = _make_analysis(rec2.id, score=50.0, kpi_json=kpi_json_fail)  # type: ignore[union-attr]

    kpi_cfg = KpiConfig(
        kpis=[
            KpiItem(
                id="cta",
                label="CTA",
                type="fact",
                weight=1.0,
                anchors=[],
                applies_to="baseline",
                include_in_score=True,
            )
        ]
    )

    result = aggregate_summary_with_kpi(
        [rec1, rec2], [ana1, ana2], manager_id, date.today(), kpi_cfg
    )

    assert len(result.kpi_stats) == 1
    stat = result.kpi_stats[0]
    assert stat.kpi_id == "cta"
    assert stat.fulfilled_pct == pytest.approx(50.0)


def test_top_issues_sorted_by_lowest_pct() -> None:
    from app.config.kpi import KpiConfig, KpiItem
    from app.services.daily_summary import aggregate_summary_with_kpi

    manager_id = uuid.uuid4()
    rec = _make_recording(manager_id)
    kpi_json = {
        "a": {"kpi_type": "fact", "value": 10.0, "quote": "", "comment": ""},
        "b": {"kpi_type": "fact", "value": 0.0, "quote": "", "comment": ""},
        "c": {"kpi_type": "fact", "value": 0.0, "quote": "", "comment": ""},
    }
    ana = _make_analysis(rec.id, score=30.0, kpi_json=kpi_json)  # type: ignore[union-attr]

    kpi_cfg = KpiConfig(
        kpis=[
            KpiItem(
                id=k,
                label=f"KPI {k.upper()}",
                type="fact",
                weight=1.0,
                anchors=[],
                applies_to="baseline",
                include_in_score=True,
            )
            for k in ("a", "b", "c")
        ]
    )

    result = aggregate_summary_with_kpi([rec], [ana], manager_id, date.today(), kpi_cfg)

    assert result.top_issues[0] in ("KPI B", "KPI C")


def test_kpi_stats_report_average_score_and_problem_areas() -> None:
    """kpi_stats carry the average score (0-10); problem areas = weak KPIs (avg < 7)."""
    from app.config.kpi import KpiConfig, KpiItem
    from app.services.daily_summary import aggregate_summary_with_kpi

    manager_id = uuid.uuid4()
    rec = _make_recording(manager_id)
    kpi_json = {
        "a": {"kpi_type": "scale", "value": 8.0, "quote": "", "comment": ""},  # good
        "b": {"kpi_type": "scale", "value": 5.0, "quote": "", "comment": ""},  # weak
        "c": {"kpi_type": "fact", "value": 10.0, "quote": "", "comment": ""},  # fulfilled
    }
    ana = _make_analysis(rec.id, score=67.0, kpi_json=kpi_json)  # type: ignore[union-attr]

    kpi_cfg = KpiConfig(
        kpis=[
            KpiItem(id="a", label="KPI A", type="scale", weight=1.0, anchors=[], applies_to="baseline", include_in_score=True),
            KpiItem(id="b", label="KPI B", type="scale", weight=1.0, anchors=[], applies_to="baseline", include_in_score=True),
            KpiItem(id="c", label="KPI C", type="fact", weight=1.0, anchors=[], applies_to="baseline", include_in_score=True),
        ]
    )

    result = aggregate_summary_with_kpi([rec], [ana], manager_id, date.today(), kpi_cfg)

    by_id = {s.kpi_id: s for s in result.kpi_stats}
    assert by_id["a"].avg_value == 8.0 and by_id["a"].kpi_type == "scale"
    assert by_id["b"].avg_value == 5.0
    assert by_id["c"].avg_value == 10.0 and by_id["c"].kpi_type == "fact"
    # only the weak KPI (avg < 7) is flagged as a problem area
    assert result.top_issues == ["KPI B"]


def test_no_problem_areas_when_all_kpis_strong() -> None:
    from app.config.kpi import KpiConfig, KpiItem
    from app.services.daily_summary import aggregate_summary_with_kpi

    manager_id = uuid.uuid4()
    rec = _make_recording(manager_id)
    kpi_json = {
        "a": {"kpi_type": "scale", "value": 8.0, "quote": "", "comment": ""},
        "b": {"kpi_type": "scale", "value": 7.0, "quote": "", "comment": ""},
        "c": {"kpi_type": "fact", "value": 10.0, "quote": "", "comment": ""},
    }
    ana = _make_analysis(rec.id, score=90.0, kpi_json=kpi_json)  # type: ignore[union-attr]
    kpi_cfg = KpiConfig(
        kpis=[
            KpiItem(id="a", label="KPI A", type="scale", weight=1.0, anchors=[], applies_to="baseline", include_in_score=True),
            KpiItem(id="b", label="KPI B", type="scale", weight=1.0, anchors=[], applies_to="baseline", include_in_score=True),
            KpiItem(id="c", label="KPI C", type="fact", weight=1.0, anchors=[], applies_to="baseline", include_in_score=True),
        ]
    )
    result = aggregate_summary_with_kpi([rec], [ana], manager_id, date.today(), kpi_cfg)
    assert result.top_issues == []
