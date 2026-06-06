"""YandexSttEngine — Yandex SpeechKit synchronous STT adapter.

Satisfies STTEngine port. Credentials (api_key, folder_id) come from
providers.yaml / env (STT_API_KEY, YANDEX_FOLDER_ID) — never hardcoded.
"""

from __future__ import annotations

import uuid
from typing import Any

import httpx
import structlog

from app.core.domain.transcript import Segment, Transcript
from app.core.ports.audio_source import AudioPayload

log = structlog.get_logger()

_YANDEX_STT_URL = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"


class YandexSttEngine:
    """Yandex SpeechKit synchronous speech-to-text adapter."""

    def __init__(
        self,
        api_key: str,
        folder_id: str,
        language: str = "ru-RU",
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key
        self._folder_id = folder_id
        self._language = language
        self._timeout = timeout

    def transcribe(self, audio: AudioPayload) -> Transcript:
        headers = {
            "Authorization": f"Api-Key {self._api_key}",
        }
        params: dict[str, Any] = {
            "folderId": self._folder_id,
            "lang": self._language,
            "format": "lpcm",
            "sampleRateHertz": audio.sample_rate,
        }
        log.info("yandex_stt.request", folder_id=self._folder_id, lang=self._language)

        resp = httpx.post(
            _YANDEX_STT_URL,
            headers=headers,
            params=params,
            content=audio.audio_data,
            timeout=self._timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        segments = self._parse_segments(data)
        full_text = " ".join(s.text for s in segments) if segments else (data.get("result") or "")
        detected = (data.get("languageCode") or self._language).split("-")[0]

        log.info("yandex_stt.done", segments=len(segments), lang=detected)
        return Transcript(
            id=uuid.uuid4(),
            recording_id=audio.manager_id,
            full_text=full_text,
            segments=tuple(segments),
            detected_language=detected,
        )

    def _parse_segments(self, data: dict[str, Any]) -> list[Segment]:
        segments: list[Segment] = []
        for chunk in data.get("chunks") or []:
            alternatives = chunk.get("alternatives") or []
            if not alternatives:
                continue
            best = alternatives[0]
            text = best.get("text") or ""
            words = best.get("words") or []
            if words:
                start = self._parse_time(words[0].get("startTime", "0s"))
                end = self._parse_time(words[-1].get("endTime", "0s"))
            else:
                start_ms = chunk.get("finalIntervalBeginMs", 0)
                end_ms = chunk.get("finalIntervalEndMs", 0)
                start = start_ms / 1000.0
                end = end_ms / 1000.0
            if end <= start:
                end = start + 0.1
            segments.append(Segment(start=start, end=end, text=text))
        return segments

    @staticmethod
    def _parse_time(value: str) -> float:
        """Parse Yandex time string like '1.5s' → 1.5."""
        return float(value.rstrip("s"))
