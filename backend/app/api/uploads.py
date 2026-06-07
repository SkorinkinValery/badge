"""POST /api/uploads — multipart audio upload endpoint."""

from __future__ import annotations

import io
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AdminRequired
from app.config.settings import Settings, get_settings
from app.core.domain.enums import RecordingStatus
from app.db.models.recording import RecordingModel
from app.db.session import get_session
from app.services.ingest import UploadValidationError, validate_upload
from app.services.storage import ObjectStorage

router = APIRouter(prefix="/api/uploads", tags=["uploads"])

_MAX_FILE_BYTES = 200 * 1024 * 1024  # 200 MB


class UploadResponse(BaseModel):
    recording_id: uuid.UUID
    status: str


def _get_storage(settings: Annotated[Settings, Depends(get_settings)]) -> ObjectStorage:
    s = ObjectStorage(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_root_user,
        secret_key=settings.minio_root_password,
        bucket=settings.minio_bucket,
    )
    s.ensure_bucket()
    return s


@router.post("", status_code=201, response_model=UploadResponse, dependencies=[AdminRequired])
async def upload_recording(
    request: Request,
    file: UploadFile,
    manager_id: Annotated[uuid.UUID, Form()],
    consent_flag: Annotated[bool, Form()],
    session: Annotated[AsyncSession, Depends(get_session)],
    storage: Annotated[ObjectStorage, Depends(_get_storage)],
    settings: Annotated[Settings, Depends(get_settings)],
    background_tasks: BackgroundTasks,
) -> UploadResponse:
    if not consent_flag:
        raise HTTPException(status_code=422, detail="consent_flag is required for recordings")

    data = await file.read()
    filename = file.filename or "upload.bin"

    try:
        validate_upload(data, filename, max_size_bytes=_MAX_FILE_BYTES)
    except UploadValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    recording_id = uuid.uuid4()
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ".bin"
    audio_key = ObjectStorage.make_key(recording_id, "original", ext)
    storage.put_object(
        audio_key,
        io.BytesIO(data),
        len(data),
        file.content_type or "application/octet-stream",
    )

    now = datetime.now(tz=UTC)
    rec = RecordingModel(
        id=recording_id,
        manager_id=manager_id,
        channel="file",
        consent_flag=consent_flag,
        audio_path=audio_key,
        status=RecordingStatus.QUEUED.value,
        created_at=now,
        retention_until=now + timedelta(days=settings.retention_days),
    )
    session.add(rec)
    await session.commit()

    from app.workers.runner import run_job  # lazy — heavy psycopg/langgraph import
    background_tasks.add_task(
        run_job,
        recording_id,
        settings.database_url,
        None,  # fail_at_stage
        getattr(request.app.state, "crm_config", None),
        getattr(request.app.state, "stt_engine", None),
        getattr(request.app.state, "analyzer", None),
        getattr(request.app.state, "storage", None),
    )

    return UploadResponse(recording_id=recording_id, status=RecordingStatus.QUEUED.value)
