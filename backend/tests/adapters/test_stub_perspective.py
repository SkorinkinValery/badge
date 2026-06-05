"""Stub perspective tests — BadgeSource/TelephonySource exist but raise NotImplementedError.

These stubs ensure the core graph is not broken when future sources are referenced
(M1 invariant: «stubs of perspective don't break the core»).
"""

from __future__ import annotations

import pytest

from app.core.ports import AudioSource


class TestBadgeSourcePerspectiveStub:
    def test_badge_source_importable(self) -> None:
        from app.adapters.audio.badge_source import BadgeSource  # noqa: F401

    def test_badge_source_implements_protocol(self) -> None:
        from app.adapters.audio.badge_source import BadgeSource
        assert isinstance(BadgeSource(), AudioSource)

    def test_badge_source_fetch_raises_not_implemented(self) -> None:
        from app.adapters.audio.badge_source import BadgeSource
        with pytest.raises(NotImplementedError):
            BadgeSource().fetch()


class TestTelephonySourcePerspectiveStub:
    def test_telephony_source_importable(self) -> None:
        from app.adapters.audio.telephony_source import TelephonySource  # noqa: F401

    def test_telephony_source_implements_protocol(self) -> None:
        from app.adapters.audio.telephony_source import TelephonySource
        assert isinstance(TelephonySource(), AudioSource)

    def test_telephony_source_fetch_raises_not_implemented(self) -> None:
        from app.adapters.audio.telephony_source import TelephonySource
        with pytest.raises(NotImplementedError):
            TelephonySource().fetch()


class TestFileStubSource:
    def test_file_stub_implements_protocol(self) -> None:
        from app.adapters.audio.file_stub import FileStubSource
        assert isinstance(FileStubSource(), AudioSource)

    def test_file_stub_fetch_returns_payload(self) -> None:
        from app.adapters.audio.file_stub import FileStubSource
        from app.core.ports import AudioPayload
        payload = FileStubSource().fetch()
        assert isinstance(payload, AudioPayload)
        assert payload.audio_data
        assert payload.sample_rate > 0


class TestStubSTTEngine:
    def test_stub_stt_implements_protocol(self) -> None:
        from app.adapters.stt.stub_stt import StubSTTEngine
        from app.core.ports import STTEngine
        assert isinstance(StubSTTEngine(), STTEngine)

    def test_stub_stt_returns_transcript(self) -> None:
        import uuid
        from datetime import UTC, datetime

        from app.adapters.stt.stub_stt import StubSTTEngine
        from app.core.domain import Transcript
        from app.core.ports import AudioPayload

        payload = AudioPayload(
            audio_data=b"\x00" * 100,
            sample_rate=16000,
            manager_id=uuid.uuid4(),
            channel="file",
            started_at=datetime.now(tz=UTC),
            consent_flag=True,
        )
        result = StubSTTEngine().transcribe(payload)
        assert isinstance(result, Transcript)
        assert result.segments
        assert result.detected_language


class TestStubAnalyzer:
    def test_stub_analyzer_implements_protocol(self) -> None:
        from app.adapters.analyzer.stub_analyzer import StubAnalyzer
        from app.core.ports import Analyzer
        assert isinstance(StubAnalyzer(), Analyzer)

    def test_stub_analyzer_returns_valid_kpi_json(self) -> None:
        import uuid

        from app.adapters.analyzer.stub_analyzer import StubAnalyzer
        from app.config.kpi import load_kpi_config
        from app.core.domain import Segment, Transcript
        from app.core.ports import AnalysisResult

        transcript = Transcript(
            id=uuid.uuid4(),
            recording_id=uuid.uuid4(),
            full_text="text",
            segments=[Segment(start=0.0, end=1.0, text="text")],
            detected_language="ru",
        )
        result = StubAnalyzer().analyze(transcript)
        assert isinstance(result, AnalysisResult)
        cfg = load_kpi_config()
        kpi_ids = {k.id for k in cfg.kpis}
        for key in result.kpi_json:
            assert key in kpi_ids


class TestJSONExporter:
    def test_json_exporter_implements_protocol(self) -> None:
        from app.adapters.crm.json_exporter import JSONExporter
        from app.core.ports import CRMExporter
        assert isinstance(JSONExporter(), CRMExporter)

    def test_json_exporter_returns_success(self, tmp_path: pytest.TempPathFactory) -> None:
        import uuid
        from datetime import UTC, datetime

        from app.adapters.crm.json_exporter import JSONExporter
        from app.core.domain import Recording, RecordingStatus
        from app.core.ports import AnalysisResult, ExportResult

        recording = Recording(
            id=uuid.uuid4(),
            manager_id=uuid.uuid4(),
            channel="file",
            consent_flag=True,
            status=RecordingStatus.DONE,
            created_at=datetime.now(tz=UTC),
            retention_until=None,
            audio_path="sample.wav",
            stage_error=None,
        )
        analysis = AnalysisResult(
            summary="Good call",
            kpi_json={"greeting": 9},
        )
        result = JSONExporter().export(analysis, recording)
        assert isinstance(result, ExportResult)
        assert result.success
