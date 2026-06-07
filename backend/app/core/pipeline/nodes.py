"""Pipeline nodes — each node corresponds to a processing stage.

Nodes call ports (not adapters directly); stubs are used in testing.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any, cast

import structlog

from app.core.domain.enums import RecordingStatus
from app.core.pipeline.state import PipelineState
from app.core.ports.analyzer import Analyzer
from app.core.ports.stt_engine import STTEngine
from app.services.storage import ObjectStorage

log = structlog.get_logger()

NodeFn = Callable[[PipelineState], PipelineState]


def _fail_state(state: PipelineState, stage: str, error: str | None = None) -> PipelineState:
    retry = (state.get("retry") or 0) + 1
    msg = error or f"injected failure in stage: {stage}"
    log.warning("stage.failed", stage=stage, retry=retry, error=msg)
    return cast(PipelineState, {
        **state,
        "status": RecordingStatus.FAILED.value,
        "stage_error": msg,
        "retry": retry,
    })


def _patch(state: PipelineState, **updates: Any) -> PipelineState:
    return cast(PipelineState, {**state, **updates})


def make_nodes(
    fail_at_stage: str | None = None,
    stt_engine: STTEngine | None = None,
    analyzer: Analyzer | None = None,
    storage: ObjectStorage | None = None,
) -> dict[str, NodeFn]:
    """Return a dict of stage node callables, optionally injecting a failure."""

    def normalizing(state: PipelineState) -> PipelineState:
        if fail_at_stage == "normalizing":
            return _fail_state(state, "normalizing")

        log.info("stage.started", stage="normalizing")

        manager_id = state.get("manager_id")
        consent_flag = bool(state.get("consent_flag", True))
        channel = str(state.get("channel") or "file")
        audio_path = state.get("audio_path")

        audio_payload: dict[str, Any]
        if storage is not None and audio_path:
            from app.services.normalize import NormalizationError, normalize_audio
            from app.services.storage import StorageKeyNotFoundError

            try:
                normalized_key = normalize_audio(
                    uuid.UUID(state["recording_id"]), audio_path, storage
                )
            except (NormalizationError, StorageKeyNotFoundError) as exc:
                log.error("stage.normalize.error", error=str(exc))
                return _fail_state(state, "normalizing", error=f"Normalization error: {exc}")

            audio_payload = {
                "normalized_key": normalized_key,
                "manager_id": manager_id,
                "consent_flag": consent_flag,
                "channel": channel,
                "sample_rate": 16000,
            }
        else:
            audio_payload = {
                "normalized_key": None,
                "manager_id": manager_id,
                "consent_flag": consent_flag,
                "channel": channel,
                "sample_rate": 16000,
            }

        log.info("stage.done", stage="normalizing")
        return _patch(
            state,
            status=RecordingStatus.NORMALIZING.value,
            audio_payload=audio_payload,
        )

    def transcribing(state: PipelineState) -> PipelineState:
        if fail_at_stage == "transcribing":
            return _fail_state(state, "transcribing")
        from datetime import UTC, datetime

        from app.core.ports import AudioPayload

        log.info("stage.started", stage="transcribing")

        engine: STTEngine
        if stt_engine is not None:
            engine = stt_engine
        else:
            from app.adapters.stt.stub_stt import StubSTTEngine
            engine = StubSTTEngine()

        audio_payload: dict[str, Any] = state.get("audio_payload") or {}
        manager_id_raw = audio_payload.get("manager_id")
        manager_id = (
            uuid.UUID(manager_id_raw)
            if manager_id_raw
            else uuid.UUID("00000000-0000-0000-0000-000000000001")
        )
        consent_flag = bool(audio_payload.get("consent_flag", True))
        channel = str(audio_payload.get("channel") or "file")
        normalized_key = audio_payload.get("normalized_key")

        if normalized_key and storage is not None:
            from app.adapters.audio.file_source import FileSource

            audio = FileSource(
                storage,
                str(normalized_key),
                manager_id,
                consent_flag,
                channel,
            ).fetch()
        else:
            from app.adapters.audio.file_stub import FileStubSource

            audio = FileStubSource().fetch()
            audio = AudioPayload(
                audio_data=audio.audio_data,
                sample_rate=audio.sample_rate,
                manager_id=manager_id,
                channel=channel,
                started_at=datetime.now(tz=UTC),
                consent_flag=consent_flag,
            )

        try:
            transcript = engine.transcribe(audio)
        except Exception as exc:
            log.error("stage.stt.error", error=str(exc))
            return _fail_state(state, "transcribing", error=f"STT error: {exc}")

        log.info(
            "stage.done",
            stage="transcribing",
            language=transcript.detected_language,
            segments=len(transcript.segments),
        )
        return _patch(
            state,
            status=RecordingStatus.TRANSCRIBING.value,
            transcript={
                "full_text": transcript.full_text,
                "detected_language": transcript.detected_language,
                "segments": [
                    {"start": s.start, "end": s.end, "text": s.text}
                    for s in transcript.segments
                ],
            },
        )

    def analyzing(state: PipelineState) -> PipelineState:
        if fail_at_stage == "analyzing":
            return _fail_state(state, "analyzing")
        from app.core.domain.transcript import Segment, Transcript

        log.info("stage.started", stage="analyzing")

        _analyzer: Analyzer
        if analyzer is not None:
            _analyzer = analyzer
        else:
            from app.adapters.analyzer.stub_analyzer import StubAnalyzer
            _analyzer = StubAnalyzer()

        t_data: dict[str, Any] = state.get("transcript") or {}
        raw_segs: list[dict[str, Any]] = t_data.get("segments") or [
            {"start": 0.0, "end": 1.0, "text": ""}
        ]
        segments = tuple(
            Segment(start=s["start"], end=s["end"], text=s["text"]) for s in raw_segs
        )
        transcript = Transcript(
            id=uuid.uuid4(),
            recording_id=uuid.UUID(state["recording_id"]),
            full_text=t_data.get("full_text") or "",
            segments=segments,
            detected_language=t_data.get("detected_language") or "ru",
        )

        try:
            result = _analyzer.analyze(transcript)
        except Exception as exc:
            log.error("stage.analyzer.error", error=str(exc))
            return _fail_state(state, "analyzing", error=f"Analyzer error: {exc}")

        log.info("stage.done", stage="analyzing")
        return _patch(
            state,
            status=RecordingStatus.ANALYZING.value,
            analysis_result={
                "summary": result.summary,
                "kpi_json": result.kpi_json,
                "mode": "baseline",
                "weights_version": None,
            },
        )

    def scoring(state: PipelineState) -> PipelineState:
        if fail_at_stage == "scoring":
            return _fail_state(state, "scoring")
        from app.config.kpi import load_kpi_config, load_weights_config
        from app.services.score import compute_score

        log.info("stage.started", stage="scoring")
        ar: dict[str, Any] = state.get("analysis_result") or {}
        kpi_json: dict[str, Any] = ar.get("kpi_json") or {}
        cfg = load_kpi_config()
        weights_cfg = load_weights_config()

        score, verdict = compute_score(kpi_json, cfg, weights_cfg)
        weights_version = f"v{sum(weights_cfg.weights.values()):.2f}"

        log.info("stage.done", stage="scoring", score=score, verdict=verdict)
        updated_ar = {**ar, "weights_version": weights_version}
        return _patch(
            state,
            status=RecordingStatus.SCORING.value,
            score=score,
            verdict=verdict,
            analysis_result=updated_ar,
        )

    def exporting(state: PipelineState) -> PipelineState:
        if fail_at_stage == "exporting":
            return _fail_state(state, "exporting")
        from datetime import UTC, datetime

        from app.adapters.crm.registry import get_exporter
        from app.core.domain.recording import Recording
        from app.core.ports import AnalysisResult

        log.info("stage.started", stage="exporting")
        ar: dict[str, Any] = state.get("analysis_result") or {}
        recording = Recording(
            id=uuid.UUID(state["recording_id"]),
            manager_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            channel="file",
            consent_flag=True,
            status=RecordingStatus.EXPORTING,
            created_at=datetime.now(tz=UTC),
            retention_until=None,
            audio_path=None,
            stage_error=None,
        )
        analysis = AnalysisResult(
            summary=ar.get("summary") or "",
            kpi_json=ar.get("kpi_json") or {},
        )

        crm_cfg: dict[str, Any] = state.get("crm_config") or {}
        crm_name: str = str(crm_cfg.get("active_crm") or "json")
        crm_params: dict[str, Any] = crm_cfg.get("params") or {}
        exporter = get_exporter(crm_name, crm_params)

        try:
            result = exporter.export(analysis, recording)
        except Exception as exc:
            log.error("stage.exporter.error", error=str(exc))
            return _fail_state(state, "exporting", error=f"Export error: {exc}")

        log.info("stage.done", stage="exporting")
        return _patch(
            state,
            status=RecordingStatus.EXPORTING.value,
            export_result={
                "success": result.success,
                "external_id": result.external_id,
            },
        )

    return {
        "normalizing": normalizing,
        "transcribing": transcribing,
        "analyzing": analyzing,
        "scoring": scoring,
        "exporting": exporting,
    }
