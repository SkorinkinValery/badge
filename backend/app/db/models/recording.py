"""Recording ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RecordingModel(Base):
    __tablename__ = "recording"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    manager_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("manager.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    channel: Mapped[str] = mapped_column(String(64), nullable=False)
    consent_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    audio_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="uploaded", index=True
    )
    stage_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    retention_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
