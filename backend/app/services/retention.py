"""Retention service — find and purge expired recordings (C1).

Cascade note:
  - TranscriptModel.recording_id FK uses ondelete="CASCADE"
  - AnalysisModel.recording_id FK uses ondelete="CASCADE"
  Both cascades are at the DB level, so deleting RecordingModel rows also
  removes associated transcript and analysis rows automatically.
  Audio objects in MinIO are deleted explicitly before removing the DB row.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.recording import RecordingModel
from app.services.storage import ObjectStorage


@dataclass
class RetentionResult:
    purged_ids: list[str] = field(default_factory=list)
    dry_run: bool = False

    @property
    def count(self) -> int:
        return len(self.purged_ids)


async def purge_expired_recordings(
    session: AsyncSession,
    storage: ObjectStorage,
    *,
    dry_run: bool = False,
    now: datetime | None = None,
) -> RetentionResult:
    """Find all recordings with retention_until < now and delete them.

    For each expired recording:
      1. Delete the audio object from MinIO (if audio_path is set).
      2. Delete the RecordingModel row from the DB.
         Associated TranscriptModel and AnalysisModel rows are removed via
         ON DELETE CASCADE at the database level.

    Args:
        session:  An async SQLAlchemy session (caller manages transaction).
        storage:  ObjectStorage instance for MinIO operations.
        dry_run:  If True, only discover candidates — nothing is deleted.
        now:      Override for "current time" (useful in tests).

    Returns:
        RetentionResult with the list of purged recording UUIDs.
    """
    effective_now = now or datetime.now(tz=UTC)

    stmt = select(RecordingModel).where(
        RecordingModel.retention_until.isnot(None),
        RecordingModel.retention_until < effective_now,
    )
    result = await session.execute(stmt)
    expired: list[RecordingModel] = list(result.scalars().all())

    purged: list[str] = []
    for rec in expired:
        purged.append(str(rec.id))
        if dry_run:
            continue
        # Delete audio object first (best-effort — ignore errors so DB delete always proceeds)
        if rec.audio_path:
            with contextlib.suppress(Exception):
                storage.delete_object(rec.audio_path)
        await session.delete(rec)

    if not dry_run and expired:
        await session.flush()

    return RetentionResult(purged_ids=purged, dry_run=dry_run)
