"""Unit tests for retention service — C5."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.anyio


def _make_recording(
    audio_path: str | None = "recordings/some-id/original.wav",
    retention_until: datetime | None = None,
) -> object:
    from app.db.models.recording import RecordingModel

    rec = MagicMock(spec=RecordingModel)
    rec.id = uuid.uuid4()
    rec.audio_path = audio_path
    rec.retention_until = retention_until
    return rec


def _past(days: int = 1) -> datetime:
    return datetime.now(tz=UTC) - timedelta(days=days)


def _future(days: int = 1) -> datetime:
    return datetime.now(tz=UTC) + timedelta(days=days)


# ---------------------------------------------------------------------------
# Retention candidate selection
# ---------------------------------------------------------------------------


class TestRetentionCandidateSelection:
    async def test_expired_recording_is_purged(self) -> None:
        """A recording with retention_until in the past is deleted."""
        from app.services.retention import purge_expired_recordings

        rec = _make_recording(retention_until=_past(5))
        storage = MagicMock()

        session = AsyncMock()
        scalars_result = MagicMock()
        scalars_result.all.return_value = [rec]
        execute_result = MagicMock()
        execute_result.scalars.return_value = scalars_result
        session.execute = AsyncMock(return_value=execute_result)
        session.delete = AsyncMock()
        session.flush = AsyncMock()

        result = await purge_expired_recordings(session, storage, dry_run=False)

        assert result.count == 1
        assert str(rec.id) in result.purged_ids
        session.delete.assert_awaited_once_with(rec)
        storage.delete_object.assert_called_once_with(rec.audio_path)

    async def test_future_recording_is_not_purged(self) -> None:
        """A recording with retention_until in the future is NOT deleted."""
        from app.services.retention import purge_expired_recordings

        storage = MagicMock()
        session = AsyncMock()
        scalars_result = MagicMock()
        scalars_result.all.return_value = []  # DB query returns nothing for future dates
        execute_result = MagicMock()
        execute_result.scalars.return_value = scalars_result
        session.execute = AsyncMock(return_value=execute_result)
        session.delete = AsyncMock()
        session.flush = AsyncMock()

        result = await purge_expired_recordings(session, storage, dry_run=False)

        assert result.count == 0
        session.delete.assert_not_awaited()
        storage.delete_object.assert_not_called()

    async def test_null_retention_is_not_purged(self) -> None:
        """A recording with retention_until=None is NOT deleted."""
        from app.services.retention import purge_expired_recordings

        storage = MagicMock()
        session = AsyncMock()
        scalars_result = MagicMock()
        scalars_result.all.return_value = []  # DB WHERE clause excludes NULL
        execute_result = MagicMock()
        execute_result.scalars.return_value = scalars_result
        session.execute = AsyncMock(return_value=execute_result)
        session.delete = AsyncMock()
        session.flush = AsyncMock()

        result = await purge_expired_recordings(session, storage, dry_run=False)

        assert result.count == 0
        session.delete.assert_not_awaited()

    async def test_multiple_expired_recordings_all_purged(self) -> None:
        """All expired recordings in the result set are deleted."""
        from app.services.retention import purge_expired_recordings

        recs = [_make_recording(retention_until=_past(i + 1)) for i in range(3)]
        storage = MagicMock()
        session = AsyncMock()
        scalars_result = MagicMock()
        scalars_result.all.return_value = recs
        execute_result = MagicMock()
        execute_result.scalars.return_value = scalars_result
        session.execute = AsyncMock(return_value=execute_result)
        session.delete = AsyncMock()
        session.flush = AsyncMock()

        result = await purge_expired_recordings(session, storage, dry_run=False)

        assert result.count == 3
        assert session.delete.await_count == 3


# ---------------------------------------------------------------------------
# dry-run mode
# ---------------------------------------------------------------------------


class TestRetentionDryRun:
    async def test_dry_run_does_not_delete_from_db(self) -> None:
        from app.services.retention import purge_expired_recordings

        rec = _make_recording(retention_until=_past(1))
        storage = MagicMock()
        session = AsyncMock()
        scalars_result = MagicMock()
        scalars_result.all.return_value = [rec]
        execute_result = MagicMock()
        execute_result.scalars.return_value = scalars_result
        session.execute = AsyncMock(return_value=execute_result)
        session.delete = AsyncMock()
        session.flush = AsyncMock()

        result = await purge_expired_recordings(session, storage, dry_run=True)

        assert result.dry_run is True
        assert result.count == 1
        assert str(rec.id) in result.purged_ids
        # Nothing was actually deleted
        session.delete.assert_not_awaited()
        storage.delete_object.assert_not_called()
        session.flush.assert_not_awaited()

    async def test_dry_run_with_multiple_records(self) -> None:
        from app.services.retention import purge_expired_recordings

        recs = [_make_recording(retention_until=_past(i + 1)) for i in range(5)]
        storage = MagicMock()
        session = AsyncMock()
        scalars_result = MagicMock()
        scalars_result.all.return_value = recs
        execute_result = MagicMock()
        execute_result.scalars.return_value = scalars_result
        session.execute = AsyncMock(return_value=execute_result)
        session.delete = AsyncMock()
        session.flush = AsyncMock()

        result = await purge_expired_recordings(session, storage, dry_run=True)

        assert result.count == 5
        session.delete.assert_not_awaited()
        storage.delete_object.assert_not_called()


# ---------------------------------------------------------------------------
# Storage error tolerance
# ---------------------------------------------------------------------------


class TestRetentionStorageErrors:
    async def test_storage_error_does_not_abort_db_delete(self) -> None:
        """If MinIO delete_object raises, the DB row is still deleted."""
        from app.services.retention import purge_expired_recordings

        rec = _make_recording(retention_until=_past(1))
        storage = MagicMock()
        storage.delete_object.side_effect = RuntimeError("MinIO unreachable")
        session = AsyncMock()
        scalars_result = MagicMock()
        scalars_result.all.return_value = [rec]
        execute_result = MagicMock()
        execute_result.scalars.return_value = scalars_result
        session.execute = AsyncMock(return_value=execute_result)
        session.delete = AsyncMock()
        session.flush = AsyncMock()

        result = await purge_expired_recordings(session, storage, dry_run=False)

        assert result.count == 1
        session.delete.assert_awaited_once_with(rec)

    async def test_recording_without_audio_path_skips_storage(self) -> None:
        """A recording with audio_path=None does not call delete_object."""
        from app.services.retention import purge_expired_recordings

        rec = _make_recording(audio_path=None, retention_until=_past(1))
        storage = MagicMock()
        session = AsyncMock()
        scalars_result = MagicMock()
        scalars_result.all.return_value = [rec]
        execute_result = MagicMock()
        execute_result.scalars.return_value = scalars_result
        session.execute = AsyncMock(return_value=execute_result)
        session.delete = AsyncMock()
        session.flush = AsyncMock()

        result = await purge_expired_recordings(session, storage, dry_run=False)

        assert result.count == 1
        storage.delete_object.assert_not_called()
        session.delete.assert_awaited_once_with(rec)


# ---------------------------------------------------------------------------
# RetentionResult dataclass
# ---------------------------------------------------------------------------


class TestRetentionResult:
    def test_count_property(self) -> None:
        from app.services.retention import RetentionResult

        r = RetentionResult(purged_ids=["a", "b", "c"])
        assert r.count == 3

    def test_empty_result(self) -> None:
        from app.services.retention import RetentionResult

        r = RetentionResult()
        assert r.count == 0
        assert r.dry_run is False
