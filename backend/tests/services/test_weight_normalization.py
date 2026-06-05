"""Unit tests for weight normalization — M4-T5."""

from __future__ import annotations

from app.config.kpi import KpiConfig, KpiItem, WeightsConfig


def _kpi(kid: str, weight: float = 1.0, applies_to: str = "baseline",
         include_in_score: bool = True, kpi_type: str = "scale") -> KpiItem:
    return KpiItem(
        id=kid, label=kid, type=kpi_type, weight=weight,
        applies_to=applies_to, include_in_score=include_in_score, anchors=[]
    )


class TestWeightNormalization:
    def test_missing_script_compliance_normalizes(self) -> None:
        """When script_compliance is absent (baseline), remaining weights sum to 100%."""
        from app.services.score import compute_score

        cfg = KpiConfig(kpis=[
            _kpi("greeting", 1.0),
            _kpi("closing", 1.0),
            _kpi("script_compliance", 2.0, applies_to="script"),
        ])
        wcfg = WeightsConfig(normalization_rule="proportional", weights={})
        kpi_json = {
            "greeting": {"value": 10.0, "quote": "q", "comment": "c"},
            "closing": {"value": 10.0, "quote": "q", "comment": "c"},
            # script_compliance absent
        }
        score, verdict = compute_score(kpi_json, cfg, wcfg)
        assert abs(score - 100.0) < 0.01
        assert verdict == "+"

    def test_baseline_and_script_comparable_on_same_kpis(self) -> None:
        """Scores are comparable when the same KPIs appear in both modes."""
        from app.services.score import compute_score

        cfg = KpiConfig(kpis=[
            _kpi("greeting", 1.0),
            _kpi("closing", 1.0),
            _kpi("script_compliance", 2.0, applies_to="script"),
        ])
        wcfg = WeightsConfig(normalization_rule="proportional", weights={})
        kpi_json_base = {
            "greeting": {"value": 7.0, "quote": "q", "comment": "c"},
            "closing": {"value": 7.0, "quote": "q", "comment": "c"},
        }
        kpi_json_script = {
            "greeting": {"value": 7.0, "quote": "q", "comment": "c"},
            "closing": {"value": 7.0, "quote": "q", "comment": "c"},
            "script_compliance": {"value": 7.0, "quote": "q", "comment": "c"},
        }
        score_base, _ = compute_score(kpi_json_base, cfg, wcfg)
        score_script, _ = compute_score(kpi_json_script, cfg, wcfg)
        # Both should give same score for the common KPIs (70.0)
        assert abs(score_base - 70.0) < 0.01
        assert abs(score_script - 70.0) < 0.01

    def test_single_kpi_still_correct(self) -> None:
        from app.services.score import compute_score

        cfg = KpiConfig(kpis=[_kpi("greeting", 1.0)])
        wcfg = WeightsConfig(normalization_rule="proportional", weights={})
        kpi_json = {"greeting": {"value": 5.0, "quote": "q", "comment": "c"}}
        score, _ = compute_score(kpi_json, cfg, wcfg)
        assert abs(score - 50.0) < 0.01

    def test_weight_override_from_weights_yaml(self) -> None:
        from app.services.score import compute_score

        cfg = KpiConfig(kpis=[
            _kpi("greeting", weight=1.0),
            _kpi("closing", weight=1.0),
        ])
        # Override: closing gets 4x weight
        wcfg = WeightsConfig(normalization_rule="proportional", weights={"closing": 4.0})
        kpi_json = {
            "greeting": {"value": 10.0, "quote": "q", "comment": "c"},
            "closing": {"value": 0.0, "quote": "q", "comment": "c"},
        }
        score, _ = compute_score(kpi_json, cfg, wcfg)
        # greeting weight=1 * 10 + closing weight=4 * 0 = 10; total_weight=5; raw=10/5=2; score=20
        assert abs(score - 20.0) < 0.01

    def test_empty_kpi_json_returns_zero(self) -> None:
        from app.services.score import compute_score

        cfg = KpiConfig(kpis=[_kpi("greeting", 1.0)])
        wcfg = WeightsConfig(normalization_rule="proportional", weights={})
        score, verdict = compute_score({}, cfg, wcfg)
        assert score == 0.0
        assert verdict == "-"

    def test_excluded_kpi_not_in_denominator(self) -> None:
        from app.services.score import compute_score

        cfg = KpiConfig(kpis=[
            _kpi("greeting", weight=1.0),
            _kpi("invisible", weight=999.0, include_in_score=False),
        ])
        wcfg = WeightsConfig(normalization_rule="proportional", weights={})
        kpi_json = {
            "greeting": {"value": 10.0, "quote": "q", "comment": "c"},
            "invisible": {"value": 0.0, "quote": "q", "comment": "c"},
        }
        score, _ = compute_score(kpi_json, cfg, wcfg)
        assert abs(score - 100.0) < 0.01
