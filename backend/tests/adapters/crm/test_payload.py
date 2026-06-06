"""Unit tests for M8-T1: common export payload serializer."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime


def _make_recording(channel: str = "file") -> object:
    from app.core.domain import Recording, RecordingStatus

    return Recording(
        id=uuid.uuid4(),
        manager_id=uuid.uuid4(),
        channel=channel,
        consent_flag=True,
        status=RecordingStatus.DONE,
        created_at=datetime(2026, 6, 6, 10, 0, 0, tzinfo=UTC),
        retention_until=None,
        audio_path="audio/test.wav",
        stage_error=None,
    )


def _make_analysis() -> object:
    from app.core.ports import AnalysisResult

    return AnalysisResult(
        summary="Клиент заинтересован, менеджер отработал возражения",
        kpi_json={"greeting": 9, "needs_discovery": 7, "close": 8},
    )


class TestBuildExportPayload:
    def test_contains_recording_id(self) -> None:
        from app.adapters.crm.payload import build_export_payload

        rec = _make_recording()
        analysis = _make_analysis()
        payload = build_export_payload(analysis, rec)  # type: ignore[arg-type]
        assert "recording_id" in payload
        assert str(rec.id) == payload["recording_id"]  # type: ignore[attr-defined]

    def test_contains_manager_id(self) -> None:
        from app.adapters.crm.payload import build_export_payload

        rec = _make_recording()
        analysis = _make_analysis()
        payload = build_export_payload(analysis, rec)  # type: ignore[arg-type]
        assert "manager_id" in payload
        assert str(rec.manager_id) == payload["manager_id"]  # type: ignore[attr-defined]

    def test_contains_channel_and_date(self) -> None:
        from app.adapters.crm.payload import build_export_payload

        rec = _make_recording(channel="mic")
        analysis = _make_analysis()
        payload = build_export_payload(analysis, rec)  # type: ignore[arg-type]
        assert payload["channel"] == "mic"
        assert "created_at" in payload

    def test_contains_summary(self) -> None:
        from app.adapters.crm.payload import build_export_payload

        rec = _make_recording()
        analysis = _make_analysis()
        payload = build_export_payload(analysis, rec)  # type: ignore[arg-type]
        assert payload["summary"] == analysis.summary  # type: ignore[attr-defined]

    def test_contains_kpi_json(self) -> None:
        from app.adapters.crm.payload import build_export_payload

        rec = _make_recording()
        analysis = _make_analysis()
        payload = build_export_payload(analysis, rec)  # type: ignore[arg-type]
        assert payload["kpi_json"] == analysis.kpi_json  # type: ignore[attr-defined]

    def test_contains_score_and_verdict_when_provided(self) -> None:
        from app.adapters.crm.payload import build_export_payload

        rec = _make_recording()
        analysis = _make_analysis()
        payload = build_export_payload(analysis, rec, score=82.5, verdict="+")  # type: ignore[arg-type]
        assert payload["score"] == 82.5
        assert payload["verdict"] == "+"

    def test_score_verdict_absent_when_not_provided(self) -> None:
        from app.adapters.crm.payload import build_export_payload

        rec = _make_recording()
        analysis = _make_analysis()
        payload = build_export_payload(analysis, rec)  # type: ignore[arg-type]
        assert payload.get("score") is None
        assert payload.get("verdict") is None

    def test_stable_keys(self) -> None:
        from app.adapters.crm.payload import build_export_payload

        rec = _make_recording()
        analysis = _make_analysis()
        payload = build_export_payload(analysis, rec)  # type: ignore[arg-type]
        required = {"recording_id", "manager_id", "channel", "created_at", "summary", "kpi_json"}
        assert required.issubset(set(payload.keys()))

    def test_serialisable_to_json(self) -> None:
        from app.adapters.crm.payload import build_export_payload

        rec = _make_recording()
        analysis = _make_analysis()
        payload = build_export_payload(analysis, rec)  # type: ignore[arg-type]
        dumped = json.dumps(payload)
        assert len(dumped) > 0
