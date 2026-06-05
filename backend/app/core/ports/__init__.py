"""Ports package — re-exports all port protocols and DTOs."""

from app.core.ports.analyzer import AnalysisResult, Analyzer
from app.core.ports.audio_source import AudioPayload, AudioSource
from app.core.ports.crm_exporter import CRMExporter, ExportResult
from app.core.ports.stt_engine import STTEngine

__all__ = [
    "AnalysisResult",
    "Analyzer",
    "AudioPayload",
    "AudioSource",
    "CRMExporter",
    "ExportResult",
    "STTEngine",
]
