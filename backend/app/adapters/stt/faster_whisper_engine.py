"""FasterWhisperEngine — self-host STT adapter via faster-whisper library.

Audio never leaves the local perimeter (ПДн invariant).
Model is loaded lazily on first transcribe call (singleton per config).
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import structlog

from app.adapters.stt.config import WhisperConfig
from app.adapters.stt.mapping import map_segments_to_transcript
from app.core.domain.transcript import Transcript
from app.core.ports.audio_source import AudioPayload

if TYPE_CHECKING:
    from faster_whisper import WhisperModel

log = structlog.get_logger()


class FasterWhisperEngine:
    """STTEngine adapter backed by faster-whisper (CTranslate2 inference)."""

    def __init__(self, config: WhisperConfig | None = None) -> None:
        self._config = config or WhisperConfig()
        self._model: WhisperModel | None = None

    def _load_model(self) -> WhisperModel:
        if self._model is None:
            from faster_whisper import WhisperModel

            log.info(
                "stt.model.loading",
                model_size=self._config.model_size,
                device=self._config.device,
                compute_type=self._config.compute_type,
            )
            self._model = WhisperModel(
                self._config.model_size,
                device=self._config.device,
                compute_type=self._config.compute_type,
            )
            log.info("stt.model.loaded", model_size=self._config.model_size)
        return self._model

    def _build_initial_prompt(self) -> str | None:
        parts: list[str] = []
        if self._config.vocabulary:
            parts.append(", ".join(self._config.vocabulary))
        if self._config.initial_prompt:
            parts.append(self._config.initial_prompt)
        return " ".join(parts) if parts else None

    def transcribe(self, audio: AudioPayload) -> Transcript:
        import io

        model = self._load_model()
        audio_bytes = (
            audio.audio_data if isinstance(audio.audio_data, bytes) else bytes(audio.audio_data)
        )

        try:
            buf = io.BytesIO(audio_bytes)
            segments_iter, info = model.transcribe(
                buf,
                language=self._config.default_language,
                vad_filter=self._config.vad_filter,
                initial_prompt=self._build_initial_prompt(),
            )
            raw_segments = list(segments_iter)
        except Exception as exc:
            log.error("stt.transcribe.failed", error=str(exc))
            return Transcript(
                id=uuid.uuid4(),
                recording_id=audio.manager_id,
                full_text="",
                segments=(),
                detected_language=self._config.default_language,
            )

        detected_language = (
            getattr(info, "language", self._config.default_language) or self._config.default_language
        )
        transcript = map_segments_to_transcript(raw_segments, audio.manager_id, detected_language)

        log.info(
            "stt.transcribe.done",
            language=detected_language,
            segments=len(transcript.segments),
            chars=len(transcript.full_text),
        )
        return transcript
