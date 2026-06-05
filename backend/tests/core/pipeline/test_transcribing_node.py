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
            "audio_data": b"\x00" * 100,
            "sample_rate": 16000,
            "channel": "file",
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


class TestTranscribingNodeDefaultEngine:
    def test_no_engine_uses_stub(self) -> None:
        """make_nodes() without stt_engine uses StubSTTEngine by default."""
        from app.core.pipeline.nodes import make_nodes

        nodes = make_nodes()
        state = _make_state()
        result = nodes["transcribing"](state)

        assert result["transcript"] is not None
        assert result["status"] == RecordingStatus.TRANSCRIBING.value
