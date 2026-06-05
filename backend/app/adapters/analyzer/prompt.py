"""LLM prompt builder for transcript analysis — M4-T2.

Builds (system_prompt, user_prompt) pair.
Rubric and anchors come from kpi.yaml — config-driven, not hardcoded.
"""

from __future__ import annotations

from typing import Any

from app.config.kpi import KpiConfig, load_kpi_config
from app.core.domain.transcript import Transcript


def _build_rubric(cfg: KpiConfig, include_script: bool) -> str:
    lines: list[str] = ["## Рубрика оценки\n"]
    for kpi in cfg.kpis:
        if kpi.applies_to == "script" and not include_script:
            continue
        lines.append(f"### {kpi.label} (id: `{kpi.id}`, тип: {kpi.type})")
        for anchor in kpi.anchors:
            lines.append(f"  - {anchor}")
        lines.append(
            "  -> Укажи `value` (0-10), `quote` - дословная цитата из транскрипта, "
            "`comment` - обоснование."
        )
        lines.append("")
    return "\n".join(lines)


def _build_few_shot(examples: list[dict[str, Any]]) -> str:
    if not examples:
        return ""
    parts = ["## Примеры оценки\n"]
    for ex in examples:
        parts.append(f"Транскрипт: {ex.get('transcript', '')}")
        parts.append(f"Ответ: {ex.get('output', '')}\n")
    return "\n".join(parts)


def build_prompt(
    transcript: Transcript,
    script: str | None = None,
    kpi_cfg: KpiConfig | None = None,
    few_shot: list[dict[str, Any]] | None = None,
) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for the LLM call.

    Baseline mode: script=None → only baseline KPIs evaluated.
    Script mode: script provided → all KPIs including script_compliance.
    """
    if kpi_cfg is None:
        kpi_cfg = load_kpi_config()

    include_script = script is not None
    rubric = _build_rubric(kpi_cfg, include_script=include_script)
    few_shot_block = _build_few_shot(few_shot or [])

    script_block = ""
    if include_script:
        script_block = f"\n## Скрипт / регламент звонка\n{script}\n"

    system = (
        "Ты — эксперт по оценке качества звонков менеджеров по продажам. "
        "Ответ верни строго в формате JSON по предоставленной схеме.\n"
        "Для каждого KPI обязательно укажи:\n"
        "- `value`: числовая оценка 0-10 (для fact-KPI только 0 или 10)\n"
        "- `quote`: дословная цитата из транскрипта (evidence)\n"
        "- `comment`: краткое обоснование оценки\n\n"
        + rubric
        + script_block
        + few_shot_block
    )

    user = (
        f"Оцени следующий транскрипт звонка:\n\n"
        f"```\n{transcript.full_text}\n```\n\n"
        f"Верни JSON по схеме."
    )

    return system, user
