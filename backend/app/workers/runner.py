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
    try:
        saver = PostgresSaver(conn)
        saver.setup()

        graph = build_graph(checkpointer=saver, fail_at_stage=fail_at_stage)

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
            except Exception:
                _crm = {"active_crm": "json", "params": {}}

        initial_state = {
            "recording_id": thread_id,
            "status": RecordingStatus.QUEUED.value,
            "stage_error": None,
            "retry": 0,
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

        engine = create_engine(db_url)
        with Session(engine) as session:
            repo = RecordingRepository(session)
            stage_error = result.get("stage_error")
            repo.update_status(
                recording_id,
                RecordingStatus(final_status),
                stage_error=stage_error,
            )
            session.commit()
        engine.dispose()

    finally:
        conn.close()
