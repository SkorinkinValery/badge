"""Integration tests for ORM models and repositories — M1-T5.

Requires a live Postgres. Set DATABASE_URL env before running:
  DATABASE_URL=postgresql+asyncpg://badge:badge@localhost:5434/badge pytest backend/tests/db/test_models.py
"""

from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://badge:badge@localhost:5434/badge",
).replace("postgresql+asyncpg://", "postgresql+psycopg2://")

pytestmark = pytest.mark.db


@pytest.fixture(scope="module")
def engine():  # type: ignore[no-untyped-def]
    import app.db.models  # noqa: F401 — registers all models
    from app.db.base import Base

    eng = create_engine(DB_URL, echo=False)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture
def session(engine):  # type: ignore[no-untyped-def]
    with Session(engine) as sess:
        yield sess
        sess.rollback()


class TestTablesExist:
    def test_manager_table_exists(self, engine) -> None:  # type: ignore[no-untyped-def]
        insp = inspect(engine)
        assert "manager" in insp.get_table_names()

    def test_script_table_exists(self, engine) -> None:  # type: ignore[no-untyped-def]
        insp = inspect(engine)
        assert "script" in insp.get_table_names()

    def test_script_ver_table_exists(self, engine) -> None:  # type: ignore[no-untyped-def]
        insp = inspect(engine)
        assert "script_ver" in insp.get_table_names()

    def test_recording_table_exists(self, engine) -> None:  # type: ignore[no-untyped-def]
        insp = inspect(engine)
        assert "recording" in insp.get_table_names()

    def test_transcript_table_exists(self, engine) -> None:  # type: ignore[no-untyped-def]
        insp = inspect(engine)
        assert "transcript" in insp.get_table_names()

    def test_analysis_table_exists(self, engine) -> None:  # type: ignore[no-untyped-def]
        insp = inspect(engine)
        assert "analysis" in insp.get_table_names()

    def test_user_table_exists(self, engine) -> None:  # type: ignore[no-untyped-def]
        insp = inspect(engine)
        assert "user" in insp.get_table_names()


class TestRecordingColumns:
    def test_recording_has_consent_flag(self, engine) -> None:  # type: ignore[no-untyped-def]
        insp = inspect(engine)
        cols = {c["name"] for c in insp.get_columns("recording")}
        assert "consent_flag" in cols

    def test_recording_has_retention_until(self, engine) -> None:  # type: ignore[no-untyped-def]
        insp = inspect(engine)
        cols = {c["name"] for c in insp.get_columns("recording")}
        assert "retention_until" in cols

    def test_recording_has_status(self, engine) -> None:  # type: ignore[no-untyped-def]
        insp = inspect(engine)
        cols = {c["name"] for c in insp.get_columns("recording")}
        assert "status" in cols

    def test_recording_has_stage_error(self, engine) -> None:  # type: ignore[no-untyped-def]
        insp = inspect(engine)
        cols = {c["name"] for c in insp.get_columns("recording")}
        assert "stage_error" in cols

    def test_recording_has_fk_to_manager(self, engine) -> None:  # type: ignore[no-untyped-def]
        insp = inspect(engine)
        fks = insp.get_foreign_keys("recording")
        referred = {fk["referred_table"] for fk in fks}
        assert "manager" in referred


class TestAnalysisColumns:
    def test_analysis_has_score(self, engine) -> None:  # type: ignore[no-untyped-def]
        insp = inspect(engine)
        cols = {c["name"] for c in insp.get_columns("analysis")}
        assert "score" in cols

    def test_analysis_has_verdict(self, engine) -> None:  # type: ignore[no-untyped-def]
        insp = inspect(engine)
        cols = {c["name"] for c in insp.get_columns("analysis")}
        assert "verdict" in cols

    def test_analysis_has_mode(self, engine) -> None:  # type: ignore[no-untyped-def]
        insp = inspect(engine)
        cols = {c["name"] for c in insp.get_columns("analysis")}
        assert "mode" in cols

    def test_analysis_has_weights_version(self, engine) -> None:  # type: ignore[no-untyped-def]
        insp = inspect(engine)
        cols = {c["name"] for c in insp.get_columns("analysis")}
        assert "weights_version" in cols

    def test_analysis_has_script_version_id(self, engine) -> None:  # type: ignore[no-untyped-def]
        insp = inspect(engine)
        cols = {c["name"] for c in insp.get_columns("analysis")}
        assert "script_version_id" in cols


class TestRepositoryCRUD:
    def test_create_and_get_manager(self, session: Session) -> None:
        from app.db.repositories.manager_repo import ManagerRepository

        repo = ManagerRepository(session)
        m = repo.create(
            full_name="Тест Тестов",
            position="Менеджер",
            device_id=None,
            is_active=True,
            default_script_id=None,
        )
        assert m.id is not None
        fetched = repo.get(m.id)
        assert fetched is not None
        assert fetched.full_name == "Тест Тестов"

    def test_create_recording_and_update_status(self, session: Session) -> None:
        from app.core.domain.enums import RecordingStatus
        from app.db.repositories.manager_repo import ManagerRepository
        from app.db.repositories.recording_repo import RecordingRepository

        mgr_repo = ManagerRepository(session)
        mgr = mgr_repo.create(
            full_name="Иван Иванов",
            position="Менеджер",
            device_id=None,
            is_active=True,
            default_script_id=None,
        )

        rec_repo = RecordingRepository(session)
        rec = rec_repo.create(
            manager_id=mgr.id,
            channel="file",
            consent_flag=True,
            audio_path="audio/test.wav",
        )
        assert rec.status == RecordingStatus.UPLOADED.value

        rec_repo.update_status(rec.id, RecordingStatus.QUEUED)
        updated = rec_repo.get(rec.id)
        assert updated is not None
        assert updated.status == RecordingStatus.QUEUED.value
