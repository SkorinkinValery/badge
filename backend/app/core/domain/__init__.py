"""Domain entities — pure core, no external dependencies."""

from app.core.domain.analysis import Analysis
from app.core.domain.enums import AnalysisMode, RecordingStatus, UserRole, Verdict
from app.core.domain.manager import Manager
from app.core.domain.recording import Recording
from app.core.domain.script import Script
from app.core.domain.transcript import Segment, Transcript
from app.core.domain.user import User

__all__ = [
    "Analysis",
    "AnalysisMode",
    "Manager",
    "Recording",
    "RecordingStatus",
    "Script",
    "Segment",
    "Transcript",
    "User",
    "UserRole",
    "Verdict",
]
