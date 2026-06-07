"""YandexGptAnalyzer — YandexGPT LLM adapter via Yandex Foundation Models API.

Satisfies Analyzer port. Credentials (api_key, folder_id) come from
providers.yaml / env (LLM_API_KEY, YANDEX_FOLDER_ID) — never hardcoded.
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

_YANDEX_GPT_URL = (
    "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
)


class YandexGptAnalyzer:
    """YandexGPT analyzer adapter — Yandex Foundation Models REST API."""

    def __init__(
        self,
        api_key: str,
        folder_id: str,
        model: str = "yandexgpt-lite/latest",
        timeout: float = 60.0,
    ) -> None:
        self._api_key = api_key
        self._folder_id = folder_id
        self._model = model
        self._timeout = timeout
        self._kpi_cfg = load_kpi_config()

    def analyze(self, transcript: Transcript, script: str | None = None) -> AnalysisResult:
        system_prompt, user_prompt = build_llm_prompt(transcript, script=script)
        headers = {
            "Authorization": f"Api-Key {self._api_key}",
            "x-folder-id": self._folder_id,
            "Content-Type": "application/json",
        }
        body: dict[str, Any] = {
            "modelUri": f"gpt://{self._folder_id}/{self._model}",
            "completionOptions": {
                "stream": False,
                "temperature": 0.0,
                "maxTokens": 2048,
            },
            "messages": [
                {"role": "system", "text": system_prompt},
                {"role": "user", "text": user_prompt},
            ],
        }
        log.info("yandex_gpt.request", model=self._model, folder=self._folder_id)

        resp = httpx.post(_YANDEX_GPT_URL, headers=headers, json=body, timeout=self._timeout)
        resp.raise_for_status()
        data = resp.json()

        raw_content = data["result"]["alternatives"][0]["message"]["text"]
        result = parse_kpi_response(
            raw_content, self._kpi_cfg, include_script=script is not None
        )
        log.info("yandex_gpt.done", kpi_count=len(result.kpi_json))
        return result
