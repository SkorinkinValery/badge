"""Transcript ORM model."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import ForeignKey, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TranscriptModel(Base):
    __tablename__ = "transcript"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    recording_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("recording.id", ondelete="CASCADE"), nullable=False, index=True
    )
    full_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    segments: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    detected_language: Mapped[str | None] = mapped_column(String(16), nullable=True)
