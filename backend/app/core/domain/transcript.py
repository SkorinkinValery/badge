"""Transcript domain entity with segments and timecodes."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict, field_validator


class Segment(BaseModel):
    model_config = ConfigDict(frozen=True)

    start: float
    end: float
    text: str


class Transcript(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    recording_id: uuid.UUID
    full_text: str
    segments: tuple[Segment, ...]
    detected_language: str

    @field_validator("segments", mode="before")
    @classmethod
    def coerce_to_tuple(cls, v: Sequence[object]) -> tuple[object, ...]:
        return tuple(v)
