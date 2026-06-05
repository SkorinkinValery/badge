"""GET /api/recordings — recording status endpoints (M2-T6)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.recording import RecordingModel
from app.db.session import get_session

router = APIRouter(prefix="/api/recordings", tags=["recordings"])


class RecordingOut(BaseModel):
    id: uuid.UUID
    manager_id: uuid.UUID
    channel: str
    status: str
    consent_flag: bool
    created_at: datetime
    audio_path: str | None
    stage_error: str | None
    retention_until: datetime | None


@router.get("", response_model=list[RecordingOut])
async def list_recordings(
    session: Annotated[AsyncSession, Depends(get_session)],
    manager_id: uuid.UUID | None = None,
) -> list[RecordingOut]:
    stmt = select(RecordingModel)
    if manager_id is not None:
        stmt = stmt.where(RecordingModel.manager_id == manager_id)
    stmt = stmt.order_by(RecordingModel.created_at.desc())
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [RecordingOut.model_validate(r, from_attributes=True) for r in rows]


@router.get("/{recording_id}", response_model=RecordingOut)
async def get_recording(
    recording_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RecordingOut:
    result = await session.execute(
        select(RecordingModel).where(RecordingModel.id == recording_id)
    )
    rec = result.scalar_one_or_none()
    if rec is None:
        raise HTTPException(status_code=404, detail="Recording not found")
    return RecordingOut.model_validate(rec, from_attributes=True)
