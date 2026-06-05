"""Unit tests for domain entities — M1-T1."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.core.domain.analysis import Analysis
from app.core.domain.enums import AnalysisMode, RecordingStatus, UserRole, Verdict
from app.core.domain.manager import Manager
from app.core.domain.recording import Recording
from app.core.domain.script import Script
from app.core.domain.transcript import Segment, Transcript
from app.core.domain.user import User

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TestEnums:
    def test_recording_status_has_required_values(self) -> None:
        expected = {
            "uploaded", "queued", "normalizing", "transcribing",
            "analyzing", "scoring", "exporting", "done", "failed",
        }
        assert {s.value for s in RecordingStatus} == expected

    def test_verdict_values(self) -> None:
        assert Verdict.POSITIVE.value == "+"
        assert Verdict.NEUTRAL.value == "~"
        assert Verdict.NEGATIVE.value == "-"

    def test_analysis_mode_values(self) -> None:
        assert AnalysisMode.BASELINE.value == "baseline"
        assert AnalysisMode.SCRIPT.value == "script"

    def test_user_role_values(self) -> None:
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.VIEWER.value == "viewer"

    def test_invalid_verdict_raises(self) -> None:
        with pytest.raises(ValueError):
            Verdict("invalid")

    def test_invalid_status_raises(self) -> None:
        with pytest.raises(ValueError):
            RecordingStatus("unknown")


# ---------------------------------------------------------------------------
# Recording
# ---------------------------------------------------------------------------

class TestRecording:
    def _make(self, **kwargs: object) -> Recording:
        defaults: dict[str, object] = {
            "id": uuid.uuid4(),
            "manager_id": uuid.uuid4(),
            "channel": "file",
            "consent_flag": True,
            "status": RecordingStatus.UPLOADED,
            "created_at": datetime.now(tz=UTC),
            "retention_until": None,
            "audio_path": None,
            "stage_error": None,
        }
        defaults.update(kwargs)
        return Recording(**defaults)  # type: ignore[arg-type]

    def test_recording_stores_required_fields(self) -> None:
        manager_id = uuid.uuid4()
        r = self._make(manager_id=manager_id, channel="telephony")
        assert r.manager_id == manager_id
        assert r.channel == "telephony"
        assert r.consent_flag is True
        assert r.status == RecordingStatus.UPLOADED

    def test_recording_has_retention_until(self) -> None:
        r = self._make(retention_until=datetime(2027, 1, 1, tzinfo=UTC))
        assert r.retention_until is not None

    def test_recording_has_stage_error(self) -> None:
        r = self._make(stage_error="stt timed out", status=RecordingStatus.FAILED)
        assert r.stage_error == "stt timed out"

    def test_recording_is_immutable(self) -> None:
        r = self._make()
        with pytest.raises((AttributeError, TypeError)):
            r.channel = "mic"  # type: ignore[misc]

    def test_recording_does_not_import_sqlalchemy(self) -> None:
        import app.core.domain.recording as mod
        src = mod.__file__ or ""
        with open(src) as f:
            assert "sqlalchemy" not in f.read()


# ---------------------------------------------------------------------------
# Transcript / Segment
# ---------------------------------------------------------------------------

class TestTranscript:
    def _make_segment(self, start: float = 0.0, end: float = 1.5) -> Segment:
        return Segment(start=start, end=end, text="Привет, как дела?")

    def test_segment_stores_timecodes(self) -> None:
        seg = self._make_segment(start=1.2, end=3.4)
        assert seg.start == pytest.approx(1.2)
        assert seg.end == pytest.approx(3.4)

    def test_transcript_stores_segments_and_language(self) -> None:
        segs = [self._make_segment(0.0, 1.0), self._make_segment(1.0, 2.5)]
        t = Transcript(
            id=uuid.uuid4(),
            recording_id=uuid.uuid4(),
            full_text="Привет, как дела? Хорошо.",
            segments=segs,
            detected_language="ru",
        )
        assert len(t.segments) == 2
        assert t.detected_language == "ru"

    def test_transcript_segments_immutable_tuple(self) -> None:
        segs = [self._make_segment()]
        t = Transcript(
            id=uuid.uuid4(),
            recording_id=uuid.uuid4(),
            full_text="text",
            segments=segs,
            detected_language="ru",
        )
        assert isinstance(t.segments, tuple)

    def test_transcript_does_not_import_sqlalchemy(self) -> None:
        import app.core.domain.transcript as mod
        src = mod.__file__ or ""
        with open(src) as f:
            assert "sqlalchemy" not in f.read()


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

class TestAnalysis:
    def _make(self, **kwargs: object) -> Analysis:
        defaults: dict[str, object] = {
            "id": uuid.uuid4(),
            "recording_id": uuid.uuid4(),
            "summary": "Менеджер хорошо отработал возражения.",
            "kpi_json": {"greeting": 8, "needs_discovery": 7},
            "score": 82.5,
            "verdict": Verdict.POSITIVE,
            "mode": AnalysisMode.BASELINE,
            "script_version_id": None,
            "weights_version": "v1",
        }
        defaults.update(kwargs)
        return Analysis(**defaults)  # type: ignore[arg-type]

    def test_analysis_stores_all_fields(self) -> None:
        a = self._make(score=90.0, verdict=Verdict.POSITIVE)
        assert a.score == pytest.approx(90.0)
        assert a.verdict == Verdict.POSITIVE
        assert a.mode == AnalysisMode.BASELINE
        assert a.weights_version == "v1"

    def test_analysis_script_mode_with_version_id(self) -> None:
        ver_id = uuid.uuid4()
        a = self._make(mode=AnalysisMode.SCRIPT, script_version_id=ver_id)
        assert a.script_version_id == ver_id

    def test_analysis_verdict_neutral(self) -> None:
        a = self._make(verdict=Verdict.NEUTRAL)
        assert a.verdict == Verdict.NEUTRAL

    def test_analysis_does_not_import_sqlalchemy(self) -> None:
        import app.core.domain.analysis as mod
        src = mod.__file__ or ""
        with open(src) as f:
            assert "sqlalchemy" not in f.read()


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------

class TestManager:
    def test_manager_stores_fields(self) -> None:
        m = Manager(
            id=uuid.uuid4(),
            full_name="Иван Петров",
            position="Менеджер по продажам",
            device_id="badge-42",
            is_active=True,
            default_script_id=None,
        )
        assert m.full_name == "Иван Петров"
        assert m.is_active is True


# ---------------------------------------------------------------------------
# Script
# ---------------------------------------------------------------------------

class TestScript:
    def test_script_stores_fields(self) -> None:
        s = Script(id=uuid.uuid4(), name="Базовый скрипт продаж", is_active=True)
        assert s.name == "Базовый скрипт продаж"
        assert s.is_active is True


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class TestUser:
    def test_user_stores_role(self) -> None:
        u = User(
            id=uuid.uuid4(),
            login="admin@company.ru",
            password_hash="$argon2...",
            role=UserRole.ADMIN,
        )
        assert u.role == UserRole.ADMIN

    def test_user_viewer_role(self) -> None:
        u = User(
            id=uuid.uuid4(),
            login="viewer@company.ru",
            password_hash="$argon2...",
            role=UserRole.VIEWER,
        )
        assert u.role == UserRole.VIEWER
