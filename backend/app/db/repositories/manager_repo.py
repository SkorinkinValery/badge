"""Manager repository."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.db.models.manager import ManagerModel


class ManagerRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        full_name: str,
        position: str,
        device_id: str | None,
        is_active: bool,
        default_script_id: uuid.UUID | None,
    ) -> ManagerModel:
        m = ManagerModel(
            id=uuid.uuid4(),
            full_name=full_name,
            position=position,
            device_id=device_id,
            is_active=is_active,
            default_script_id=default_script_id,
        )
        self._session.add(m)
        self._session.flush()
        return m

    def get(self, manager_id: uuid.UUID) -> ManagerModel | None:
        return self._session.get(ManagerModel, manager_id)
