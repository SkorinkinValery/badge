"""Tests for exporting node — M4-T7."""

from __future__ import annotations

from typing import Any


def _make_state_after_scoring() -> dict[str, Any]:
    import uuid
    from app.core.domain.enums import RecordingStatus

    return {
        "recording_id": str(uuid.uuid4()),
        "status": RecordingStatus.SCORING.value,
        "stage_error": None,
        "retry": 0,
        "audio_payload": None,
        "transcript": {
            "full_text": "Добрый день",
            "detected_language": "ru",
            "segments": [],
        },
        "analysis_result": {
            "summary": "Хорошая работа",
            "kpi_json": {"greeting": 8},
            "mode": "baseline",
            "weights_version": "v10.0",
        },
        "score": 80.0,
        "verdict": "+",
        "export_result": None,
    }


class TestExportingNode:
    def test_exporting_sets_export_result(self) -> None:
        from app.core.pipeline.nodes import make_nodes

        nodes = make_nodes()
        result = nodes["exporting"](_make_state_after_scoring())
        assert result["export_result"] is not None

    def test_exporting_sets_success_true(self) -> None:
        from app.core.pipeline.nodes import make_nodes

        nodes = make_nodes()
        result = nodes["exporting"](_make_state_after_scoring())
        assert result["export_result"]["success"] is True

    def test_exporting_sets_external_id(self) -> None:
        from app.core.pipeline.nodes import make_nodes

        nodes = make_nodes()
        result = nodes["exporting"](_make_state_after_scoring())
        assert result["export_result"]["external_id"]

    def test_exporting_status_set(self) -> None:
        from app.core.domain.enums import RecordingStatus
        from app.core.pipeline.nodes import make_nodes

        nodes = make_nodes()
        result = nodes["exporting"](_make_state_after_scoring())
        assert result["status"] == RecordingStatus.EXPORTING.value

    def test_exporting_failure_sets_failed(self) -> None:
        from app.core.domain.enums import RecordingStatus
        from app.core.pipeline.nodes import make_nodes

        nodes = make_nodes(fail_at_stage="exporting")
        result = nodes["exporting"](_make_state_after_scoring())
        assert result["status"] == RecordingStatus.FAILED.value
        assert "exporting" in result["stage_error"]

    def test_full_graph_reaches_done(self) -> None:
        from langgraph.checkpoint.memory import MemorySaver
        from app.core.pipeline.graph import build_graph
        from app.core.domain.enums import RecordingStatus
        import uuid

        graph = build_graph(checkpointer=MemorySaver())
        rid = uuid.uuid4()
        state = {
            "recording_id": str(rid),
            "status": RecordingStatus.QUEUED.value,
            "stage_error": None, "retry": 0,
            "audio_payload": None, "transcript": None,
            "analysis_result": None, "score": None,
            "verdict": None, "export_result": None,
        }
        result = graph.invoke(state, config={"configurable": {"thread_id": str(rid)}})
        assert result["status"] == RecordingStatus.DONE.value
        assert result["export_result"]["success"] is True
