"""PipelineState — LangGraph state schema for the processing pipeline."""

from __future__ import annotations

from typing import Any

from typing_extensions import TypedDict


class PipelineState(TypedDict, total=False):
    recording_id: str
    status: str
    stage_error: str | None
    retry: int
    audio_payload: dict[str, Any] | None
    transcript: dict[str, Any] | None
    analysis_result: dict[str, Any] | None
    score: float | None
    verdict: str | None
    export_result: dict[str, Any] | None
    crm_config: dict[str, Any] | None
