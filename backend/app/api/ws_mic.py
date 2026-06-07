"""WebSocket endpoint for near-realtime microphone capture (M7-T4).

Protocol: `start` → `chunk*` → `stop`
Auth: JWT passed as query param `?token=...` (browsers cannot send
  Authorization headers in WebSocket upgrade requests).
"""

from __future__ import annotations

import asyncio
import io
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.adapters.audio.mic_protocol import (
    AckMsg,
    ChunkMsg,
    ErrorMsg,
    PartialTranscriptMsg,
    ProtocolError,
    SessionProtocol,
    StartMsg,
    StopMsg,
    parse_client_msg,
)
from app.core.domain.enums import RecordingStatus
from app.core.ports.audio_source import AudioPayload
from app.db.models.recording import RecordingModel
from app.services.auth import decode_token
from app.services.mic_buffer import BufferOverflowError, ChunkBuffer

log = structlog.get_logger(__name__)

router = APIRouter(tags=["ws_mic"])

_DEFAULT_RETENTION_DAYS = 90


def _get_stt(app: Any) -> Any:
    """Return the configured STT engine from app.state."""
    engine = getattr(app.state, "stt_engine", None)
    if engine is None:
        log.error("ws_mic.stt_engine_missing", detail="app.state.stt_engine not set; check providers.yaml")
        from app.adapters.stt.stub_stt import StubSTTEngine
        return StubSTTEngine()
    return engine


async def _run_stt(stt: Any, payload: AudioPayload) -> str:
    """Run synchronous STT in a thread pool to avoid blocking the event loop."""
    loop = asyncio.get_event_loop()
    transcript = await loop.run_in_executor(None, stt.transcribe, payload)
    return str(transcript.full_text)


def _kick_pipeline(
    recording_id: uuid.UUID,
    db_url: str,
    stt_engine: Any,
    analyzer: Any,
    crm_config: dict[str, Any] | None,
    storage: Any = None,
) -> None:
    """Fire-and-forget: run the processing pipeline in a background thread."""
    import concurrent.futures

    from app.workers.runner import run_job  # lazy — heavy psycopg/langgraph import

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    executor.submit(
        run_job,
        recording_id,
        db_url,
        None,  # fail_at_stage
        crm_config,
        stt_engine,
        analyzer,
        storage,
    )
    executor.shutdown(wait=False)


async def _create_recording(
    session_factory: Any,
    manager_id: uuid.UUID,
    channel: str,
    consent_flag: bool,
) -> uuid.UUID:
    """Insert a new recording row and return its id."""
    now = datetime.now(tz=UTC)
    recording_id = uuid.uuid4()
    rec = RecordingModel(
        id=recording_id,
        manager_id=manager_id,
        channel=channel,
        consent_flag=consent_flag,
        audio_path=None,
        status=RecordingStatus.UPLOADED.value,
        created_at=now,
        retention_until=now + timedelta(days=_DEFAULT_RETENTION_DAYS),
    )
    async with session_factory() as session:
        session.add(rec)
        await session.commit()
    return recording_id


async def _persist_mic_audio(
    session_factory: Any,
    storage: Any,
    recording_id: uuid.UUID,
    data: bytes,
) -> str | None:
    """Upload accumulated mic audio (WebM container) to object storage and
    record its key on the recording row, so the pipeline can normalize and
    transcribe the real captured audio (not a stub).

    Returns the storage key, or None if storage is unavailable.
    """
    if storage is None:
        log.error("ws_mic.storage_missing", recording_id=str(recording_id))
        return None

    from app.services.storage import ObjectStorage

    audio_key = ObjectStorage.make_key(recording_id, "original", ".webm")
    storage.put_object(audio_key, io.BytesIO(data), len(data), "audio/webm")

    async with session_factory() as session:
        result = await session.execute(
            select(RecordingModel).where(RecordingModel.id == recording_id)
        )
        rec = result.scalar_one_or_none()
        if rec is not None:
            rec.audio_path = audio_key
            await session.commit()
    return audio_key


async def _set_status(
    session_factory: Any,
    recording_id: uuid.UUID,
    status: RecordingStatus,
    stage_error: str | None = None,
) -> None:
    async with session_factory() as session:
        result = await session.execute(
            select(RecordingModel).where(RecordingModel.id == recording_id)
        )
        rec = result.scalar_one_or_none()
        if rec is not None:
            rec.status = status.value
            if stage_error is not None:
                rec.stage_error = stage_error
            await session.commit()


@router.websocket("/api/ws/mic")
async def ws_mic(
    websocket: WebSocket,
    token: str | None = Query(default=None),
) -> None:
    """Near-realtime mic capture WS endpoint.

    Client message sequence: start → chunk* → stop
    Server sends: ack | partial_transcript | error
    """
    settings = websocket.app.state.settings
    session_factory = websocket.app.state.session_factory
    stt = _get_stt(websocket.app)

    # ── Authenticate BEFORE accept() to prevent unauthenticated connections ──
    user_sub: str | None = None
    if token:
        try:
            payload = decode_token(token, settings.jwt_secret)
            user_sub = payload.get("sub")
        except Exception as exc:
            log.warning("ws_mic.auth_failed", error=str(exc))

    if not user_sub:
        await websocket.close(code=1008)
        return

    await websocket.accept()

    # ── Session state ────────────────────────────────────────────────────────
    proto = SessionProtocol()
    buf = ChunkBuffer(
        window_bytes=settings.mic_window_bytes,
        max_bytes=settings.mic_max_bytes,
    )
    # Full audio accumulator — WebM container must stay intact for Whisper.
    # Window-based partial STT is disabled: MediaRecorder produces streaming WebM
    # where only the first chunk carries the EBML header; arbitrary byte-slicing
    # breaks the container and causes Whisper decode failures.
    audio_accum: bytearray = bytearray()
    seen_seqs_audio: set[int] = set()
    recording_id: uuid.UUID | None = None
    active_start: StartMsg | None = None

    log.info("ws_mic.connected", sub=user_sub)

    try:
        async for raw in websocket.iter_text():
            # Parse + validate ordering
            try:
                msg = parse_client_msg(raw)
                proto.validate(msg)
            except ProtocolError as exc:
                await websocket.send_text(
                    ErrorMsg(code="PROTOCOL_ERROR", message=str(exc)).model_dump_json()
                )
                continue

            # ── start ────────────────────────────────────────────────────────
            if isinstance(msg, StartMsg):
                if not msg.consent_flag:
                    await websocket.send_text(
                        ErrorMsg(
                            code="CONSENT_REQUIRED",
                            message="consent_flag must be true (ПДн requirement)",
                        ).model_dump_json()
                    )
                    continue

                active_start = msg
                recording_id = await _create_recording(
                    session_factory,
                    manager_id=msg.manager_id,
                    channel=msg.channel,
                    consent_flag=msg.consent_flag,
                )
                log.info(
                    "ws_mic.recording_created",
                    recording_id=str(recording_id),
                    manager_id=str(msg.manager_id),
                )
                await websocket.send_text(
                    AckMsg(message=f"recording {recording_id} created").model_dump_json()
                )

            # ── chunk ────────────────────────────────────────────────────────
            elif isinstance(msg, ChunkMsg):
                chunk_data = msg.decode_data()
                # Accumulate for final transcription (dedup by seq)
                if msg.seq not in seen_seqs_audio:
                    seen_seqs_audio.add(msg.seq)
                    audio_accum.extend(chunk_data)
                try:
                    buf.add(msg.seq, chunk_data)  # overflow guard + protocol dedup
                except BufferOverflowError as exc:
                    await websocket.send_text(
                        ErrorMsg(code="BUFFER_OVERFLOW", message=str(exc)).model_dump_json()
                    )
                    await websocket.close(code=1011)
                    return

                await websocket.send_text(AckMsg(seq=msg.seq).model_dump_json())

            # ── stop ─────────────────────────────────────────────────────────
            elif isinstance(msg, StopMsg):
                if audio_accum and active_start is not None:
                    audio = AudioPayload(
                        audio_data=bytes(audio_accum),
                        sample_rate=16000,
                        manager_id=active_start.manager_id,
                        channel=active_start.channel,
                        started_at=datetime.now(tz=UTC),
                        consent_flag=active_start.consent_flag,
                    )
                    text = await _run_stt(stt, audio)
                    await websocket.send_text(
                        PartialTranscriptMsg(text=text, is_final=True).model_dump_json()
                    )

                if recording_id is not None:
                    storage = getattr(websocket.app.state, "storage", None)
                    if audio_accum:
                        await _persist_mic_audio(
                            session_factory, storage, recording_id, bytes(audio_accum)
                        )
                    await _set_status(session_factory, recording_id, RecordingStatus.QUEUED)
                    log.info("ws_mic.queued", recording_id=str(recording_id))
                    _kick_pipeline(
                        recording_id,
                        settings.database_url,
                        stt_engine=stt,
                        analyzer=getattr(websocket.app.state, "analyzer", None),
                        crm_config=getattr(websocket.app.state, "crm_config", None),
                        storage=storage,
                    )

                await websocket.close()
                return

    except WebSocketDisconnect:
        log.info("ws_mic.disconnect", recording_id=str(recording_id))
        if recording_id is not None:
            try:
                await _set_status(
                    session_factory,
                    recording_id,
                    RecordingStatus.FAILED,
                    stage_error="WebSocket disconnected",
                )
            except Exception as exc:
                log.warning("ws_mic.cleanup_failed", error=str(exc))
