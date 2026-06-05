"""Pure scoring function: kpi_json + weights → score (0-100) + verdict — M4-T4/T5.

No I/O, no side effects — fully deterministic and testable.
Handles both plain numeric values (stub) and rich dict entries (LLM output).
"""

from __future__ import annotations

from typing import Any

from app.config.kpi import KpiConfig, WeightsConfig

_VERDICT_PLUS = "+"
_VERDICT_NEUTRAL = "~"
_VERDICT_MINUS = "-"
_THRESHOLD_PLUS = 80.0
_THRESHOLD_NEUTRAL = 50.0


def _extract_value(entry: Any) -> float:
    """Extract numeric score from either plain number or dict entry."""
    if isinstance(entry, dict):
        return float(entry.get("value", 0.0))
    return float(entry)


def compute_score(
    kpi_json: dict[str, Any],
    kpi_cfg: KpiConfig,
    weights_cfg: WeightsConfig,
) -> tuple[float, str]:
    """Compute weighted score and verdict from kpi_json.

    Returns (score 0-100, verdict '+' | '~' | '-').
    KPIs missing from kpi_json or with include_in_score=False are excluded;
    weights are normalised proportionally over the available set.
    """
    available = [
        k for k in kpi_cfg.kpis
        if k.include_in_score and k.id in kpi_json
    ]
    if not available:
        return 0.0, _VERDICT_MINUS

    total_weight = sum(
        weights_cfg.weights.get(k.id, k.weight) for k in available
    )
    if total_weight == 0.0:
        return 0.0, _VERDICT_MINUS

    weighted_sum = sum(
        _extract_value(kpi_json[k.id]) * weights_cfg.weights.get(k.id, k.weight)
        for k in available
    )
    raw_score = weighted_sum / total_weight
    score = round((raw_score / 10.0) * 100.0, 2)

    if score >= _THRESHOLD_PLUS:
        verdict = _VERDICT_PLUS
    elif score >= _THRESHOLD_NEUTRAL:
        verdict = _VERDICT_NEUTRAL
    else:
        verdict = _VERDICT_MINUS

    return score, verdict
