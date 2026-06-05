"""User domain entity."""

from __future__ import annotations

import uuid

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

from app.core.domain.enums import UserRole


@dataclass(config=ConfigDict(frozen=True))
class User:
    id: uuid.UUID
    login: str
    password_hash: str
    role: UserRole
