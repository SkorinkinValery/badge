"""GigaChatAnalyzer — Sber GigaChat LLM adapter via OpenAI-compatible REST API.

Satisfies Analyzer port. auth_token comes from env (LLM_API_KEY / GIGACHAT_TOKEN)
— never hardcoded.
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from app.adapters.analyzer.ru_llm_base import build_llm_prompt, parse_kpi_response
from app.config.kpi import load_kpi_config
from app.core.domain.transcript import Transcript
from app.core.ports.analyzer import AnalysisResult

log = structlog.get_logger()

_GIGACHAT_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"


class GigaChatAnalyzer:
    """GigaChat analyzer adapter — Sber OpenAI-compatible chat completions API."""

    def __init__(
        self,
        auth_token: str,
        scope: str = "GIGACHAT_API_PERS",
        model: str = "GigaChat:latest",
        timeout: float = 60.0,
    ) -> None:
        self._auth_token = auth_token
        self._scope = scope
        self._model = model
        self._timeout = timeout
        self._kpi_cfg = load_kpi_config()

    def analyze(self, transcript: Transcript, script: str | None = None) -> AnalysisResult:
        system_prompt, user_prompt = build_llm_prompt(transcript, script=script)
        headers = {
            "Authorization": f"Bearer {self._auth_token}",
            "X-Scope": self._scope,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        body: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }
        log.info("gigachat.request", model=self._model)

        resp = httpx.post(_GIGACHAT_URL, headers=headers, json=body, timeout=self._timeout)
        resp.raise_for_status()
        data = resp.json()

        raw_content = data["choices"][0]["message"]["content"]
        result = parse_kpi_response(raw_content, self._kpi_cfg)
        log.info("gigachat.done", kpi_count=len(result.kpi_json))
        return result
