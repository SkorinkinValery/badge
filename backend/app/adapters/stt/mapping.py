"""Mapping faster-whisper segments → domain Transcript — M3-T3."""

from __future__ import annotations

import uuid
from typing import Any

from app.core.domain.transcript import Segment, Transcript


def map_segments_to_transcript(
    raw_segments: list[Any],
    recording_id: uuid.UUID,
    detected_language: str,
) -> Transcript:
    """Convert faster-whisper segment list to a domain Transcript."""
    domain_segments = tuple(
        Segment(start=s.start, end=s.end, text=s.text.strip())
        for s in raw_segments
        if s.end > s.start
    )
    full_text = " ".join(s.text for s in domain_segments).strip()
    return Transcript(
        id=uuid.uuid4(),
        recording_id=recording_id,
        full_text=full_text,
        segments=domain_segments,
        detected_language=detected_language,
    )
