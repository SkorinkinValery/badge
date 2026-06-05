"""GET /api/recordings — recording status and transcript endpoints (M2-T6, M3-T6)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.recording import RecordingModel
from app.db.models.transcript import TranscriptModel
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


class SegmentOut(BaseModel):
    start: float
    end: float
    text: str


class TranscriptOut(BaseModel):
    recording_id: uuid.UUID
    full_text: str
    segments: list[SegmentOut]
    detected_language: str


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


@router.get("/{recording_id}/transcript", response_model=TranscriptOut)
async def get_transcript(
    recording_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TranscriptOut:
    result = await session.execute(
        select(TranscriptModel).where(TranscriptModel.recording_id == recording_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Transcript not found")

    raw_segments: list[Any] = row.segments or []
    segments = [
        SegmentOut(start=s["start"], end=s["end"], text=s["text"])
        for s in raw_segments
    ]
    return TranscriptOut(
        recording_id=recording_id,
        full_text=row.full_text or "",
        segments=segments,
        detected_language=row.detected_language or "",
    )


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
