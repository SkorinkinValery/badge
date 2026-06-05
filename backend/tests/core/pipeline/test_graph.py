"""Integration tests for LangGraph pipeline graph — M1-T6.

Uses MemorySaver for in-process tests; optional PostgresSaver for DB tests.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from app.core.domain.enums import RecordingStatus


def make_initial_state(recording_id: uuid.UUID | None = None) -> dict[str, Any]:
    return {
        "recording_id": str(recording_id or uuid.uuid4()),
        "status": RecordingStatus.QUEUED.value,
        "stage_error": None,
        "retry": 0,
        "audio_payload": None,
        "transcript": None,
        "analysis_result": None,
        "score": None,
        "verdict": None,
        "export_result": None,
    }


class TestGraphDefinition:
    def test_graph_importable(self) -> None:
        from app.core.pipeline.graph import build_graph  # noqa: F401

    def test_state_importable(self) -> None:
        from app.core.pipeline.state import PipelineState  # noqa: F401

    def test_nodes_importable(self) -> None:
        from app.core.pipeline import nodes  # noqa: F401

    def test_graph_has_required_nodes(self) -> None:
        from langgraph.checkpoint.memory import MemorySaver

        from app.core.pipeline.graph import build_graph

        graph = build_graph(checkpointer=MemorySaver())
        node_names = set(graph.nodes)
        assert "normalizing" in node_names
        assert "transcribing" in node_names
        assert "analyzing" in node_names
        assert "scoring" in node_names
        assert "exporting" in node_names


class TestGraphHappyPath:
    def test_graph_runs_to_done(self) -> None:
        from langgraph.checkpoint.memory import MemorySaver

        from app.core.pipeline.graph import build_graph

        graph = build_graph(checkpointer=MemorySaver())
        recording_id = uuid.uuid4()
        state = make_initial_state(recording_id)
        config = {"configurable": {"thread_id": str(recording_id)}}

        result = graph.invoke(state, config=config)
        assert result["status"] == RecordingStatus.DONE.value

    def test_status_progresses_through_stages(self) -> None:
        from langgraph.checkpoint.memory import MemorySaver

        from app.core.pipeline.graph import build_graph

        statuses_seen: list[str] = []

        graph = build_graph(
            checkpointer=MemorySaver(),
            on_status_change=lambda s: statuses_seen.append(s),
        )
        recording_id = uuid.uuid4()
        state = make_initial_state(recording_id)
        config = {"configurable": {"thread_id": str(recording_id)}}

        graph.invoke(state, config=config)
        expected_order = [
            RecordingStatus.NORMALIZING.value,
            RecordingStatus.TRANSCRIBING.value,
            RecordingStatus.ANALYZING.value,
            RecordingStatus.SCORING.value,
            RecordingStatus.EXPORTING.value,
            RecordingStatus.DONE.value,
        ]
        for expected in expected_order:
            assert expected in statuses_seen, f"Status {expected!r} not seen"

    def test_graph_result_has_score(self) -> None:
        from langgraph.checkpoint.memory import MemorySaver

        from app.core.pipeline.graph import build_graph

        graph = build_graph(checkpointer=MemorySaver())
        recording_id = uuid.uuid4()
        state = make_initial_state(recording_id)
        config = {"configurable": {"thread_id": str(recording_id)}}

        result = graph.invoke(state, config=config)
        assert result["score"] is not None
        assert isinstance(result["score"], float)

    def test_graph_result_has_export(self) -> None:
        from langgraph.checkpoint.memory import MemorySaver

        from app.core.pipeline.graph import build_graph

        graph = build_graph(checkpointer=MemorySaver())
        recording_id = uuid.uuid4()
        state = make_initial_state(recording_id)
        config = {"configurable": {"thread_id": str(recording_id)}}

        result = graph.invoke(state, config=config)
        assert result["export_result"] is not None


class TestGraphFailureBranch:
    def test_failing_node_sets_failed_status(self) -> None:
        from langgraph.checkpoint.memory import MemorySaver

        from app.core.pipeline.graph import build_graph

        graph = build_graph(checkpointer=MemorySaver(), fail_at_stage="transcribing")
        recording_id = uuid.uuid4()
        state = make_initial_state(recording_id)
        config = {"configurable": {"thread_id": str(recording_id)}}

        result = graph.invoke(state, config=config)
        assert result["status"] == RecordingStatus.FAILED.value
        assert result["stage_error"] is not None
        assert "transcribing" in result["stage_error"]

    def test_failed_status_has_retry_count(self) -> None:
        from langgraph.checkpoint.memory import MemorySaver

        from app.core.pipeline.graph import build_graph

        graph = build_graph(checkpointer=MemorySaver(), fail_at_stage="analyzing")
        recording_id = uuid.uuid4()
        state = make_initial_state(recording_id)
        config = {"configurable": {"thread_id": str(recording_id)}}

        result = graph.invoke(state, config=config)
        assert result["retry"] >= 1

    def test_graph_does_not_loop_infinitely_on_failure(self) -> None:
        from langgraph.checkpoint.memory import MemorySaver

        from app.core.pipeline.graph import build_graph

        graph = build_graph(checkpointer=MemorySaver(), fail_at_stage="normalizing")
        recording_id = uuid.uuid4()
        state = make_initial_state(recording_id)
        config = {"configurable": {"thread_id": str(recording_id)}}

        result = graph.invoke(state, config=config)
        assert result["status"] == RecordingStatus.FAILED.value
        assert result["retry"] <= 3


class TestGraphCheckpointer:
    def test_checkpointer_persists_state(self) -> None:
        from langgraph.checkpoint.memory import MemorySaver

        from app.core.pipeline.graph import build_graph

        saver = MemorySaver()
        graph = build_graph(checkpointer=saver)
        recording_id = uuid.uuid4()
        thread_id = str(recording_id)
        state = make_initial_state(recording_id)
        config = {"configurable": {"thread_id": thread_id}}

        graph.invoke(state, config=config)

        checkpoint = saver.get(config)
        assert checkpoint is not None

    def test_graph_with_postgres_checkpointer(self) -> None:
        """Runs only when Postgres is available (integration)."""
        import os
        db_url = os.environ.get(
            "DATABASE_URL",
            "postgresql://badge:badge@localhost:5434/badge",
        ).replace("postgresql+asyncpg://", "postgresql://")

        try:
            import psycopg
            from langgraph.checkpoint.postgres import PostgresSaver

            conn = psycopg.connect(db_url, autocommit=True)
            saver = PostgresSaver(conn)
            saver.setup()
        except Exception as exc:
            pytest.skip(f"Postgres checkpointer not available: {exc}")

        from app.core.pipeline.graph import build_graph

        graph = build_graph(checkpointer=saver)
        recording_id = uuid.uuid4()
        state = make_initial_state(recording_id)
        config = {"configurable": {"thread_id": str(recording_id)}}

        result = graph.invoke(state, config=config)
        assert result["status"] == RecordingStatus.DONE.value
        conn.close()
