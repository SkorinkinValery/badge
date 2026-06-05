"""Script and ScriptVersion ORM models."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ScriptModel(Base):
    __tablename__ = "script"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    active_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)


class ScriptVerModel(Base):
    __tablename__ = "script_ver"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    script_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("script.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    kpi_binding: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
