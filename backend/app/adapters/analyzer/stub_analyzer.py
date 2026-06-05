"""StubAnalyzer — deterministic LLM analyzer for CI/offline development.

Selected via providers.yaml (active_llm=stub) — ensures core autonomy without API keys.
Returns fixed summary and KPI scores that are valid against the configured kpi.yaml.
"""

from __future__ import annotations

from app.config.kpi import load_kpi_config
from app.core.domain.transcript import Transcript
from app.core.ports.analyzer import AnalysisResult


class StubAnalyzer:
    """Returns deterministic analysis. Satisfies Analyzer protocol."""

    def analyze(self, transcript: Transcript, script: str | None = None) -> AnalysisResult:
        cfg = load_kpi_config()
        kpi_json = {kpi.id: 7 for kpi in cfg.kpis if kpi.applies_to == "baseline"}
        if script is not None:
            kpi_json.update(
                {kpi.id: 8 for kpi in cfg.kpis if kpi.applies_to == "script"}
            )
        return AnalysisResult(
            summary=(
                "Стаб-анализ: менеджер представился, выявил потребность, "
                "провёл презентацию и отработал возражения."
            ),
            kpi_json=kpi_json,
        )
