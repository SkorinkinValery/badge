"""LangGraph pipeline graph — normalizing → transcribing → analyzing → scoring → exporting."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, StateGraph

from app.core.domain.enums import RecordingStatus
from app.core.pipeline.nodes import NodeFn, make_nodes
from app.core.pipeline.state import PipelineState

_MAX_RETRY = 3


def _is_failed(state: PipelineState) -> bool:
    return state.get("status") == RecordingStatus.FAILED.value


def build_graph(
    checkpointer: BaseCheckpointSaver[Any],
    fail_at_stage: str | None = None,
    on_status_change: Callable[[str], None] | None = None,
) -> Any:
    """Build and compile the processing graph.

    Args:
        checkpointer: LangGraph checkpointer (MemorySaver or PostgresSaver).
        fail_at_stage: Inject a failure at a specific stage (for testing).
        on_status_change: Optional callback fired with each new status string.
    """
    raw_nodes = make_nodes(fail_at_stage=fail_at_stage)
    nodes: dict[str, NodeFn]

    if on_status_change is not None:
        cb = on_status_change

        def _wrap(name: str, fn: NodeFn) -> NodeFn:
            def wrapped(state: PipelineState) -> PipelineState:
                result = fn(state)
                cb(result.get("status") or "")
                return result

            wrapped.__name__ = name
            return wrapped

        nodes = {name: _wrap(name, fn) for name, fn in raw_nodes.items()}
    else:
        nodes = raw_nodes

    def _done_node(state: PipelineState) -> PipelineState:
        new_status = RecordingStatus.DONE.value
        if on_status_change is not None:
            on_status_change(new_status)
        return cast(PipelineState, {**state, "status": new_status})

    builder: StateGraph[PipelineState, Any, Any] = StateGraph(PipelineState)

    for name, fn in nodes.items():
        builder.add_node(name, fn)  # type: ignore[call-overload]

    builder.add_node("done", _done_node)
    builder.add_node("failed", lambda s: s)

    builder.set_entry_point("normalizing")

    def _route(state: PipelineState) -> str:
        return "failed" if _is_failed(state) else "continue"

    for stage, next_stage in [
        ("normalizing", "transcribing"),
        ("transcribing", "analyzing"),
        ("analyzing", "scoring"),
        ("scoring", "exporting"),
    ]:
        builder.add_conditional_edges(
            stage,
            _route,
            {"failed": "failed", "continue": next_stage},
        )

    builder.add_conditional_edges(
        "exporting",
        _route,
        {"failed": "failed", "continue": "done"},
    )

    builder.add_edge("done", END)
    builder.add_edge("failed", END)

    return builder.compile(checkpointer=checkpointer)
