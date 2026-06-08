"""OpenAICompatibleAnalyzer — LLM-based transcript analysis via OpenAI-compatible API.

Works with gpt-4o-mini, vLLM, and any OpenAI-compatible endpoint.
base_url / model / api_key come exclusively from providers.yaml / env — never hardcoded.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import structlog

from app.adapters.analyzer.prompt import build_prompt
from app.adapters.analyzer.schema import (
    KpiEntry,
    applicable_kpis,
    build_kpi_result_model,
)
from app.config.kpi import load_kpi_config
from app.config.settings import LLMProviderConfig
from app.core.domain.transcript import Transcript
from app.core.ports.analyzer import AnalysisResult

if TYPE_CHECKING:
    pass

log = structlog.get_logger()


class OpenAICompatibleAnalyzer:
    """Analyzer adapter using OpenAI-compatible chat completion API."""

    def __init__(self, config: LLMProviderConfig) -> None:
        self._config = config
        self._kpi_cfg = load_kpi_config()
        self._client = self._build_client()

    def _build_client(self) -> Any:
        from openai import OpenAI

        return OpenAI(
            api_key=self._config.api_key or "no-key",
            base_url=self._config.base_url,
        )

    def analyze(self, transcript: Transcript, script: str | None = None) -> AnalysisResult:
        include_script = script is not None
        kpi_model = build_kpi_result_model(self._kpi_cfg, include_script=include_script)
        system_prompt, user_prompt = build_prompt(
            transcript, script=script, kpi_cfg=self._kpi_cfg
        )
        log.info(
            "analyzer.request",
            model=self._config.model,
            transcript_len=len(transcript.full_text),
        )

        try:
            create_kwargs: dict[str, Any] = {
                "model": self._config.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.0,
            }
            if self._config.structured_output_mode == "guided_json":
                create_kwargs["extra_body"] = {
                    "guided_json": kpi_model.model_json_schema()
                }
            else:
                create_kwargs["response_format"] = {"type": "json_object"}

            response = self._client.chat.completions.create(**create_kwargs)
            raw_content = response.choices[0].message.content or "{}"
        except Exception as exc:
            log.error("analyzer.request.failed", error=str(exc))
            raise

        try:
            parsed = json.loads(raw_content)
            kpi_result = kpi_model.model_validate(parsed)
        except Exception as exc:
            log.error("analyzer.parse.failed", error=str(exc), content=raw_content[:200])
            raise ValueError(f"LLM response failed schema validation: {exc}") from exc

        kpi_json: dict[str, Any] = {}
        for kpi in applicable_kpis(self._kpi_cfg, include_script):
            entry: KpiEntry = getattr(kpi_result, kpi.id)
            kpi_json[kpi.id] = {
                "value": entry.value,
                "quote": entry.quote,
                "comment": entry.comment,
            }

        summary = self._build_summary(kpi_json, transcript)

        log.info(
            "analyzer.done",
            model=self._config.model,
            kpi_count=len(kpi_json),
        )
        return AnalysisResult(summary=summary, kpi_json=kpi_json)

    def _build_summary(self, kpi_json: dict[str, Any], transcript: Transcript) -> str:
        labels = {k.id: k.label for k in self._kpi_cfg.kpis}
        high = [
            labels.get(kid, kid)
            for kid, v in kpi_json.items()
            if isinstance(v, dict) and v.get("value", 0) >= 8
        ]
        low = [
            labels.get(kid, kid)
            for kid, v in kpi_json.items()
            if isinstance(v, dict) and v.get("value", 10) <= 3
        ]
        parts: list[str] = [f"Транскрипт: {len(transcript.full_text)} симв."]
        if high:
            parts.append(f"Сильные стороны: {', '.join(high)}.")
        if low:
            parts.append(f"Зоны роста: {', '.join(low)}.")
        return " ".join(parts)
