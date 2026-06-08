"""Shared KPI parsing logic for RU-cloud LLM adapters (M9-T4)."""

from __future__ import annotations

import json
from typing import Any

from app.adapters.analyzer.prompt import build_prompt
from app.adapters.analyzer.schema import (
    KpiEntry,
    applicable_kpis,
    build_kpi_result_model,
)
from app.config.kpi import KpiConfig, load_kpi_config
from app.core.domain.transcript import Transcript
from app.core.ports.analyzer import AnalysisResult


def parse_kpi_response(
    raw_content: str,
    kpi_cfg: KpiConfig,
    include_script: bool = False,
) -> AnalysisResult:
    """Parse raw LLM JSON output into AnalysisResult using KpiResult schema.

    In baseline mode (include_script=False) script-only KPIs are neither
    required nor extracted, matching what the prompt asked the LLM for.
    """
    kpi_model = build_kpi_result_model(kpi_cfg, include_script=include_script)
    parsed = json.loads(raw_content)
    kpi_result = kpi_model.model_validate(parsed)

    kpi_json: dict[str, Any] = {}
    for kpi in applicable_kpis(kpi_cfg, include_script):
        entry: KpiEntry = getattr(kpi_result, kpi.id)
        kpi_json[kpi.id] = {
            "value": entry.value,
            "quote": entry.quote,
            "comment": entry.comment,
        }

    labels = {k.id: k.label for k in kpi_cfg.kpis}
    high = [
        labels.get(k, k)
        for k, v in kpi_json.items()
        if isinstance(v, dict) and v.get("value", 0) >= 8
    ]
    low = [
        labels.get(k, k)
        for k, v in kpi_json.items()
        if isinstance(v, dict) and v.get("value", 10) <= 3
    ]
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
