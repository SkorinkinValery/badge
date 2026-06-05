"""Contract tests for port signatures — M1-T2."""

from __future__ import annotations

import inspect
import uuid
from datetime import UTC, datetime

from app.core.domain import Recording, RecordingStatus
from app.core.ports import (
    AnalysisResult,
    Analyzer,
    AudioPayload,
    AudioSource,
    CRMExporter,
    ExportResult,
    STTEngine,
)


def _make_recording() -> Recording:
    return Recording(
        id=uuid.uuid4(),
        manager_id=uuid.uuid4(),
        channel="file",
        consent_flag=True,
        status=RecordingStatus.DONE,
        created_at=datetime.now(tz=UTC),
        retention_until=None,
        audio_path="path/to/audio.wav",
        stage_error=None,
    )


class TestPortsAreProtocols:
    def test_audio_source_is_protocol(self) -> None:
        assert hasattr(AudioSource, "__protocol_attrs__") or hasattr(
            AudioSource, "_is_protocol"
        )

    def test_stt_engine_is_protocol(self) -> None:
        assert hasattr(STTEngine, "__protocol_attrs__") or hasattr(
            STTEngine, "_is_protocol"
        )

    def test_analyzer_is_protocol(self) -> None:
        assert hasattr(Analyzer, "__protocol_attrs__") or hasattr(
            Analyzer, "_is_protocol"
        )

    def test_crm_exporter_is_protocol(self) -> None:
        assert hasattr(CRMExporter, "__protocol_attrs__") or hasattr(
            CRMExporter, "_is_protocol"
        )

    def test_ports_are_runtime_checkable(self) -> None:
        assert getattr(AudioSource, "_is_runtime_protocol", False)
        assert getattr(STTEngine, "_is_runtime_protocol", False)
        assert getattr(Analyzer, "_is_runtime_protocol", False)
        assert getattr(CRMExporter, "_is_runtime_protocol", False)


class TestAudioSourceSignature:
    def test_fetch_method_exists(self) -> None:
        assert hasattr(AudioSource, "fetch")

    def test_fetch_signature(self) -> None:
        sig = inspect.signature(AudioSource.fetch)
        # fetch(self) -> AudioPayload — return annotation must be present
        assert sig.return_annotation is not inspect.Parameter.empty

    def test_audio_payload_has_required_fields(self) -> None:
        payload = AudioPayload(
            audio_data=b"\x00\x01",
            sample_rate=16000,
            manager_id=uuid.uuid4(),
            channel="file",
            started_at=datetime.now(tz=UTC),
            consent_flag=True,
        )
        assert payload.audio_data == b"\x00\x01"
        assert payload.sample_rate == 16000
        assert payload.consent_flag is True


class TestSTTEngineSignature:
    def test_transcribe_method_exists(self) -> None:
        assert hasattr(STTEngine, "transcribe")

    def test_transcribe_signature_has_audio_param(self) -> None:
        sig = inspect.signature(STTEngine.transcribe)
        assert "audio" in sig.parameters


class TestAnalyzerSignature:
    def test_analyze_method_exists(self) -> None:
        assert hasattr(Analyzer, "analyze")

    def test_analyze_has_transcript_and_optional_script(self) -> None:
        sig = inspect.signature(Analyzer.analyze)
        params = list(sig.parameters)
        assert "transcript" in params
        # script should exist as optional parameter
        assert "script" in params

    def test_analysis_result_has_required_fields(self) -> None:
        result = AnalysisResult(
            summary="Хорошо отработал возражения",
            kpi_json={"greeting": 8},
        )
        assert result.summary
        assert isinstance(result.kpi_json, dict)


class TestCRMExporterSignature:
    def test_export_method_exists(self) -> None:
        assert hasattr(CRMExporter, "export")

    def test_export_signature_has_analysis_and_recording(self) -> None:
        sig = inspect.signature(CRMExporter.export)
        params = list(sig.parameters)
        assert "analysis" in params
        assert "recording" in params

    def test_export_result_has_success_flag(self) -> None:
        result = ExportResult(success=True, external_id="row-42")
        assert result.success is True
        assert result.external_id == "row-42"

    def test_export_result_failure(self) -> None:
        result = ExportResult(success=False, error="timeout")
        assert result.success is False
        assert result.error == "timeout"


class TestPortsDoNotImportAdapters:
    def test_ports_module_clean(self) -> None:
        import app.core.ports as ports_mod
        src_file = ports_mod.__file__ or ""
        with open(src_file) as f:
            content = f.read()
        assert "adapters" not in content
