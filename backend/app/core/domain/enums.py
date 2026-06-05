"""Domain enumerations — shared by all domain entities."""

from __future__ import annotations

from enum import StrEnum


class RecordingStatus(StrEnum):
    UPLOADED = "uploaded"
    QUEUED = "queued"
    NORMALIZING = "normalizing"
    TRANSCRIBING = "transcribing"
    ANALYZING = "analyzing"
    SCORING = "scoring"
    EXPORTING = "exporting"
    DONE = "done"
    FAILED = "failed"


class Verdict(StrEnum):
    POSITIVE = "+"
    NEUTRAL = "~"
    NEGATIVE = "-"


class AnalysisMode(StrEnum):
    BASELINE = "baseline"
    SCRIPT = "script"


class UserRole(StrEnum):
    ADMIN = "admin"
    VIEWER = "viewer"
