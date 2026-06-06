"""Shared KPI parsing logic for RU-cloud LLM adapters (M9-T4)."""

from __future__ import annotations

import json
from typing import Any

from app.adapters.analyzer.prompt import build_prompt
from app.adapters.analyzer.schema import KpiEntry, build_kpi_result_model
from app.config.kpi import KpiConfig, load_kpi_config
from app.core.domain.transcript import Transcript
from app.core.ports.analyzer import AnalysisResult


def parse_kpi_response(
    raw_content: str,
    kpi_cfg: KpiConfig,
) -> AnalysisResult:
    """Parse raw LLM JSON output into AnalysisResult using KpiResult schema."""
    kpi_model = build_kpi_result_model(kpi_cfg)
    parsed = json.loads(raw_content)
    kpi_result = kpi_model.model_validate(parsed)

    kpi_json: dict[str, Any] = {}
    for kpi in kpi_cfg.kpis:
        entry: KpiEntry = getattr(kpi_result, kpi.id)
        kpi_json[kpi.id] = {
            "value": entry.value,
            "quote": entry.quote,
            "comment": entry.comment,
        }

    high = [k for k, v in kpi_json.items() if isinstance(v, dict) and v.get("value", 0) >= 8]
    low = [k for k, v in kpi_json.items() if isinstance(v, dict) and v.get("value", 10) <= 3]
    parts = [f"KPI проанализированы: {len(kpi_json)}."]
    if high:
        parts.append(f"Сильные стороны: {', '.join(high)}.")
    if low:
        parts.append(f"Зоны роста: {', '.join(low)}.")
    summary = " ".join(parts)

    return AnalysisResult(summary=summary, kpi_json=kpi_json)


def build_llm_prompt(transcript: Transcript, script: str | None = None) -> tuple[str, str]:
    kpi_cfg = load_kpi_config()
    return build_prompt(transcript, script=script, kpi_cfg=kpi_cfg)
