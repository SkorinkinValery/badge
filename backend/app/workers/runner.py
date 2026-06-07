"""Graph job runner — picks up a queued recording and drives it through the pipeline.

Idempotent: running the same recording_id twice resumes from the checkpoint.
"""

from __future__ import annotations

import uuid

import structlog
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.domain.enums import RecordingStatus
from app.core.pipeline.graph import build_graph
from app.db.repositories.recording_repo import RecordingRepository

log = structlog.get_logger()


def run_job(
    recording_id: uuid.UUID,
    db_url: str,
    fail_at_stage: str | None = None,
    crm_config: dict[str, object] | None = None,
    stt_engine: object | None = None,
    analyzer: object | None = None,
    storage: object | None = None,
) -> None:
    """Run the processing graph for a single recording.

    Connects to Postgres checkpointer so the run can be resumed from
    the last completed stage if interrupted.

    Args:
        recording_id: UUID of the recording to process.
        db_url: psycopg2-compatible DATABASE_URL.
        fail_at_stage: Inject a failure for testing purposes.
    """
    import psycopg
    from langgraph.checkpoint.postgres import PostgresSaver
    from psycopg.rows import dict_row

    sync_url = db_url.replace("postgresql+psycopg2://", "postgresql://").replace(
        "postgresql+asyncpg://", "postgresql://"
    )

    conn = psycopg.connect(sync_url, autocommit=True, row_factory=dict_row)
    engine = create_engine(sync_url)
    try:
        saver = PostgresSaver(conn)
        saver.setup()

        graph = build_graph(
            checkpointer=saver,
            fail_at_stage=fail_at_stage,
            stt_engine=stt_engine,  # type: ignore[arg-type]
            analyzer=analyzer,  # type: ignore[arg-type]
            storage=storage,  # type: ignore[arg-type]
        )

        thread_id = str(recording_id)
        config = {"configurable": {"thread_id": thread_id}}

        _crm: dict[str, object]
        if crm_config is not None:
            _crm = crm_config
        else:
            try:
                from app.config.settings import load_providers_config
                providers = load_providers_config()
                _crm = {"active_crm": providers.active_crm, "params": providers.crm_params()}
            except Exception as exc:
                log.error("runner.providers_config_failed", error=str(exc))
                _crm = {"active_crm": "json", "params": {}}

        with Session(engine) as session:
            recording = RecordingRepository(session).get(recording_id)
            if recording is None:
                raise ValueError(f"recording not found: {recording_id}")
            audio_path = recording.audio_path
            manager_id = str(recording.manager_id)
            consent_flag = recording.consent_flag
            channel = recording.channel

        initial_state = {
            "recording_id": thread_id,
            "status": RecordingStatus.QUEUED.value,
            "stage_error": None,
            "retry": 0,
            "audio_path": audio_path,
            "manager_id": manager_id,
            "consent_flag": consent_flag,
            "channel": channel,
            "audio_payload": None,
            "transcript": None,
            "analysis_result": None,
            "score": None,
            "verdict": None,
            "export_result": None,
            "crm_config": _crm,
        }

        log.info("runner.start", recording_id=thread_id)
        result = graph.invoke(initial_state, config=config)
        final_status = result.get("status", RecordingStatus.FAILED.value)
        log.info("runner.done", recording_id=thread_id, status=final_status)

        with Session(engine) as session:
            repo = RecordingRepository(session)
            stage_error = result.get("stage_error")
            repo.update_status(
                recording_id,
                RecordingStatus(final_status),
                stage_error=stage_error,
            )
            _persist_results(session, recording_id, result)
            session.commit()

    finally:
        conn.close()
        engine.dispose()


def _persist_results(
    session: Session, recording_id: uuid.UUID, result: dict[str, object]
) -> None:
    """Upsert transcript + analysis computed by the pipeline.

    The graph keeps everything in PipelineState; without this the rich
    transcript/KPI output is lost and the API returns 404 for them.
    Idempotent: re-running a recording overwrites prior rows.
    """
    from sqlalchemy import select

    from app.db.models.analysis import AnalysisModel
    from app.db.models.transcript import TranscriptModel

    transcript = result.get("transcript")
    if isinstance(transcript, dict):
        row = session.execute(
            select(TranscriptModel).where(TranscriptModel.recording_id == recording_id)
        ).scalar_one_or_none()
        if row is None:
            row = TranscriptModel(recording_id=recording_id)
            session.add(row)
        row.full_text = transcript.get("full_text")
        row.segments = transcript.get("segments")
        row.detected_language = transcript.get("detected_language")

    analysis = result.get("analysis_result")
    if isinstance(analysis, dict):
        row_a = session.execute(
            select(AnalysisModel).where(AnalysisModel.recording_id == recording_id)
        ).scalar_one_or_none()
        score = result.get("score")
        if row_a is None:
            row_a = AnalysisModel(recording_id=recording_id)
            session.add(row_a)
        row_a.summary = analysis.get("summary")
        row_a.kpi_json = analysis.get("kpi_json")
        row_a.score = score  # type: ignore[assignment]
        # Preserve auto_score from the original automatic run (manual PATCH may
        # later override `score`); only set it if not already recorded.
        if row_a.auto_score is None:
            row_a.auto_score = score  # type: ignore[assignment]
        row_a.verdict = result.get("verdict")  # type: ignore[assignment]
        row_a.mode = analysis.get("mode") or "baseline"
        row_a.weights_version = analysis.get("weights_version")
