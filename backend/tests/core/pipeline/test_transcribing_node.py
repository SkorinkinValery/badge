"""Tests for transcribing node integration with STTEngine port — M3-T4."""

from __future__ import annotations

import uuid
from typing import Any

from app.core.domain.enums import RecordingStatus


def _make_state(recording_id: uuid.UUID | None = None) -> dict[str, Any]:
    return {
        "recording_id": str(recording_id or uuid.uuid4()),
        "status": RecordingStatus.NORMALIZING.value,
        "stage_error": None,
        "retry": 0,
        "audio_payload": {
            "normalized_key": None,
            "manager_id": "00000000-0000-0000-0000-000000000001",
            "consent_flag": True,
            "channel": "file",
            "sample_rate": 16000,
        },
        "transcript": None,
        "analysis_result": None,
        "score": None,
        "verdict": None,
        "export_result": None,
    }


class TestTranscribingNodeHappyPath:
    def test_transcribing_sets_transcript_in_state(self) -> None:
        from app.adapters.stt.stub_stt import StubSTTEngine
        from app.core.pipeline.nodes import make_nodes

        nodes = make_nodes(stt_engine=StubSTTEngine())
        state = _make_state()
        result = nodes["transcribing"](state)

        assert result["transcript"] is not None
        t = result["transcript"]
        assert isinstance(t["full_text"], str)
        assert len(t["full_text"]) > 0

    def test_transcribing_sets_segments(self) -> None:
        from app.adapters.stt.stub_stt import StubSTTEngine
        from app.core.pipeline.nodes import make_nodes

        nodes = make_nodes(stt_engine=StubSTTEngine())
        state = _make_state()
        result = nodes["transcribing"](state)

        segments = result["transcript"]["segments"]
        assert len(segments) > 0
        assert all("start" in s and "end" in s and "text" in s for s in segments)

    def test_transcribing_sets_detected_language(self) -> None:
        from app.adapters.stt.stub_stt import StubSTTEngine
        from app.core.pipeline.nodes import make_nodes

        nodes = make_nodes(stt_engine=StubSTTEngine())
        state = _make_state()
        result = nodes["transcribing"](state)

        assert result["transcript"]["detected_language"]

    def test_transcribing_sets_transcribing_status(self) -> None:
        from app.adapters.stt.stub_stt import StubSTTEngine
        from app.core.pipeline.nodes import make_nodes

        nodes = make_nodes(stt_engine=StubSTTEngine())
        state = _make_state()
        result = nodes["transcribing"](state)

        assert result["status"] == RecordingStatus.TRANSCRIBING.value


class TestTranscribingNodeFailurePath:
    def test_stt_error_sets_failed_status(self) -> None:
        from app.core.pipeline.nodes import make_nodes

        nodes = make_nodes(fail_at_stage="transcribing")
        state = _make_state()
        result = nodes["transcribing"](state)

        assert result["status"] == RecordingStatus.FAILED.value
        assert result["stage_error"] is not None
        assert "transcribing" in result["stage_error"]

    def test_stt_error_increments_retry(self) -> None:
        from app.core.pipeline.nodes import make_nodes

        nodes = make_nodes(fail_at_stage="transcribing")
        state = _make_state()
        result = nodes["transcribing"](state)

        assert result["retry"] >= 1

    def test_stt_engine_exception_sets_failed(self) -> None:
        """A broken STT engine (raises) → failed state, not exception propagation."""
        from app.core.pipeline.nodes import make_nodes

        class BrokenSTT:
            def transcribe(self, audio: object) -> None:  # type: ignore[override]
                raise RuntimeError("STT crashed")

        nodes = make_nodes(stt_engine=BrokenSTT())  # type: ignore[arg-type]
        state = _make_state()
        result = nodes["transcribing"](state)

        assert result["status"] == RecordingStatus.FAILED.value
        assert result["stage_error"] is not None


class TestTranscribingNodeRealAudio:
    def test_fetches_real_bytes_via_file_source_when_normalized_key_present(self) -> None:
        """When audio_payload carries a normalized_key and storage is injected,
        the node must fetch real bytes via FileSource — not the silent stub —
        otherwise STT always transcribes silence regardless of the uploaded audio."""
        from io import BytesIO

        from app.core.domain.transcript import Segment, Transcript
        from app.core.pipeline.nodes import make_nodes

        captured: dict[str, Any] = {}

        class FakeEngine:
            def transcribe(self, audio: Any) -> Transcript:
                captured["audio"] = audio
                return Transcript(
                    id=uuid.uuid4(),
                    recording_id=uuid.uuid4(),
                    full_text="реальный текст",
                    segments=(Segment(start=0.0, end=1.0, text="реальный текст"),),
                    detected_language="ru",
                )

        class FakeStorage:
            def get_object(self, key: str) -> BytesIO:
                captured["key"] = key
                return BytesIO(b"REAL-AUDIO-BYTES")

        nodes = make_nodes(stt_engine=FakeEngine(), storage=FakeStorage())  # type: ignore[arg-type]
        state = _make_state()
        state["audio_payload"] = {
            "normalized_key": "recordings/abc/normalized.wav",
            "manager_id": "11111111-1111-1111-1111-111111111111",
            "consent_flag": True,
            "channel": "file",
            "sample_rate": 16000,
        }
        result = nodes["transcribing"](state)

        assert captured["key"] == "recordings/abc/normalized.wav"
        assert captured["audio"].audio_data == b"REAL-AUDIO-BYTES"
        assert str(captured["audio"].manager_id) == "11111111-1111-1111-1111-111111111111"
        assert result["transcript"]["full_text"] == "реальный текст"
        assert result["status"] == RecordingStatus.TRANSCRIBING.value

    def test_falls_back_to_stub_when_no_normalized_key(self) -> None:
        """No normalized_key (e.g. legacy recordings, unit tests without MinIO)
        → stub audio source, exactly like the no-storage path."""
        from app.core.pipeline.nodes import make_nodes

        class FakeStorage:
            def get_object(self, key: str) -> Any:
                raise AssertionError("storage.get_object must not be called without normalized_key")

        nodes = make_nodes(storage=FakeStorage())  # type: ignore[arg-type]
        state = _make_state()
        result = nodes["transcribing"](state)

        assert result["status"] == RecordingStatus.TRANSCRIBING.value
        assert result["transcript"] is not None


class TestTranscribingNodeDefaultEngine:
    def test_no_engine_uses_stub(self) -> None:
        """make_nodes() without stt_engine uses StubSTTEngine by default."""
        from app.core.pipeline.nodes import make_nodes

        nodes = make_nodes()
        state = _make_state()
        result = nodes["transcribing"](state)

        assert result["transcript"] is not None
        assert result["status"] == RecordingStatus.TRANSCRIBING.value
