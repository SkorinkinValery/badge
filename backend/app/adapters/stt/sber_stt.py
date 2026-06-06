"""SberSttEngine — Sber SaluteSpeech synchronous STT adapter.

Satisfies STTEngine port. auth_token comes from env (STT_API_KEY / SBER_AUTH_TOKEN)
— never hardcoded.
"""

from __future__ import annotations

import uuid
from typing import Any

import httpx
import structlog

from app.core.domain.transcript import Segment, Transcript
from app.core.ports.audio_source import AudioPayload

log = structlog.get_logger()

_SBER_STT_URL = "https://smartspeech.sber.ru/rest/v1/speech:recognize"


class SberSttEngine:
    """Sber SaluteSpeech synchronous speech-to-text adapter."""

    def __init__(
        self,
        auth_token: str,
        language: str = "ru-RU",
        timeout: float = 30.0,
    ) -> None:
        self._auth_token = auth_token
        self._language = language
        self._timeout = timeout

    def transcribe(self, audio: AudioPayload) -> Transcript:
        headers = {
            "Authorization": f"Bearer {self._auth_token}",
            "Content-Type": "audio/x-pcm;bit=16;rate=16000",
        }
        params: dict[str, Any] = {
            "language": self._language,
        }
        log.info("sber_stt.request", lang=self._language)

        resp = httpx.post(
            _SBER_STT_URL,
            headers=headers,
            params=params,
            content=audio.audio_data,
            timeout=self._timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        segments = self._parse_segments(data)
        full_text = " ".join(s.text for s in segments)
        detected = (data.get("language") or self._language).split("-")[0]

        log.info("sber_stt.done", segments=len(segments), lang=detected)
        return Transcript(
            id=uuid.uuid4(),
            recording_id=audio.manager_id,
            full_text=full_text,
            segments=tuple(segments),
            detected_language=detected,
        )

    def _parse_segments(self, data: dict[str, Any]) -> list[Segment]:
        segments: list[Segment] = []
        for item in data.get("result") or []:
            results = item.get("results") or []
            if not results:
                continue
            best = results[0]
            text = best.get("transcript") or ""
            words = best.get("words") or []
            if words:
                start = words[0].get("start_ms", 0) / 1000.0
                end = words[-1].get("end_ms", 0) / 1000.0
            else:
                start, end = 0.0, 0.1
            if end <= start:
                end = start + 0.1
            segments.append(Segment(start=start, end=end, text=text))
        return segments
