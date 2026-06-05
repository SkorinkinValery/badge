"""Script repository — sync (used in tests and seeding)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.script import ScriptModel, ScriptVerModel


class ScriptRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, name: str) -> ScriptModel:
        s = ScriptModel(id=uuid.uuid4(), name=name, is_active=True, active_version_id=None)
        self._session.add(s)
        self._session.flush()
        return s

    def get(self, script_id: uuid.UUID) -> ScriptModel | None:
        return self._session.get(ScriptModel, script_id)

    def list_all(self) -> list[ScriptModel]:
        return list(self._session.execute(select(ScriptModel)).scalars().all())

    def create_version(
        self,
        script_id: uuid.UUID,
        content: str,
        kpi_binding: dict[str, Any] | None = None,
    ) -> ScriptVerModel:
        existing = self._session.execute(
            select(ScriptVerModel)
            .where(ScriptVerModel.script_id == script_id)
            .order_by(ScriptVerModel.version.desc())
        ).scalar_one_or_none()
        next_version = (existing.version + 1) if existing else 1
        ver = ScriptVerModel(
            id=uuid.uuid4(),
            script_id=script_id,
            version=next_version,
            content=content,
            kpi_binding=kpi_binding,
        )
        self._session.add(ver)
        self._session.flush()
        return ver

    def list_versions(self, script_id: uuid.UUID) -> list[ScriptVerModel]:
        return list(
            self._session.execute(
                select(ScriptVerModel)
                .where(ScriptVerModel.script_id == script_id)
                .order_by(ScriptVerModel.version)
            ).scalars().all()
        )

    def set_active_version(
        self, script_id: uuid.UUID, version_id: uuid.UUID
    ) -> ScriptModel | None:
        s = self.get(script_id)
        if s is None:
            return None
        s.active_version_id = version_id
        self._session.flush()
        return s

    def get_active_version(self, script_id: uuid.UUID) -> ScriptVerModel | None:
        s = self.get(script_id)
        if s is None or s.active_version_id is None:
            return None
        return self._session.get(ScriptVerModel, s.active_version_id)
