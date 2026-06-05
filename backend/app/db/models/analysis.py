"""Analysis ORM model."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Float, ForeignKey, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AnalysisModel(Base):
    __tablename__ = "analysis"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    recording_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("recording.id", ondelete="CASCADE"), nullable=False, index=True
    )
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    kpi_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    auto_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    verdict: Mapped[str | None] = mapped_column(String(4), nullable=True)
    mode: Mapped[str] = mapped_column(String(16), nullable=False, default="baseline")
    script_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    weights_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    corrected_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
