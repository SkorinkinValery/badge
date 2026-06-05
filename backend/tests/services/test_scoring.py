"""Unit tests for pure scoring function — M4-T4."""

from __future__ import annotations

import pytest


def _make_kpi_json(ids: list[str], value: float) -> dict[str, object]:
    return {kid: {"value": value, "quote": "q", "comment": "c"} for kid in ids}


class TestScoringFunction:
    def test_score_importable(self) -> None:
        from app.services.score import compute_score  # noqa: F401

    def test_all_max_score_gives_100(self) -> None:
        from app.config.kpi import load_kpi_config, load_weights_config
        from app.services.score import compute_score

        cfg = load_kpi_config()
        wcfg = load_weights_config()
        kpi_ids = [k.id for k in cfg.kpis if k.include_in_score]
        kpi_json = _make_kpi_json(kpi_ids, 10.0)
        score, _ = compute_score(kpi_json, cfg, wcfg)
        assert abs(score - 100.0) < 0.01

    def test_all_zero_score_gives_0(self) -> None:
        from app.config.kpi import load_kpi_config, load_weights_config
        from app.services.score import compute_score

        cfg = load_kpi_config()
        wcfg = load_weights_config()
        kpi_ids = [k.id for k in cfg.kpis if k.include_in_score]
        kpi_json = _make_kpi_json(kpi_ids, 0.0)
        score, _ = compute_score(kpi_json, cfg, wcfg)
        assert abs(score) < 0.01

    def test_verdict_plus_for_high_score(self) -> None:
        from app.config.kpi import load_kpi_config, load_weights_config
        from app.services.score import compute_score

        cfg = load_kpi_config()
        wcfg = load_weights_config()
        kpi_ids = [k.id for k in cfg.kpis if k.include_in_score]
        kpi_json = _make_kpi_json(kpi_ids, 10.0)
        _, verdict = compute_score(kpi_json, cfg, wcfg)
        assert verdict == "+"

    def test_verdict_minus_for_low_score(self) -> None:
        from app.config.kpi import load_kpi_config, load_weights_config
        from app.services.score import compute_score

        cfg = load_kpi_config()
        wcfg = load_weights_config()
        kpi_ids = [k.id for k in cfg.kpis if k.include_in_score]
        kpi_json = _make_kpi_json(kpi_ids, 0.0)
        _, verdict = compute_score(kpi_json, cfg, wcfg)
        assert verdict == "-"

    def test_include_in_score_false_excluded(self) -> None:
        from app.config.kpi import KpiConfig, KpiItem, WeightsConfig, load_kpi_config
        from app.services.score import compute_score

        # KPI with include_in_score=False should not affect score
        base_cfg = load_kpi_config()
        kpis = list(base_cfg.kpis)
        # Make first KPI excluded, give it 0
        excluded = kpis[0]
        kpi_json = {excluded.id: {"value": 0.0, "quote": "q", "comment": "c"}}
        # Also add an included KPI with high score
        included = next(k for k in kpis if k.id != excluded.id and k.include_in_score)
        kpi_json[included.id] = {"value": 10.0, "quote": "q", "comment": "c"}

        cfg2 = KpiConfig(kpis=[
            KpiItem(**{**excluded.model_dump(), "include_in_score": False}),
            included,
        ])
        wcfg = WeightsConfig(normalization_rule="proportional", weights={})
        score, _ = compute_score(kpi_json, cfg2, wcfg)
        assert score == 100.0

    def test_deterministic_same_input_same_output(self) -> None:
        from app.config.kpi import load_kpi_config, load_weights_config
        from app.services.score import compute_score

        cfg = load_kpi_config()
        wcfg = load_weights_config()
        kpi_ids = [k.id for k in cfg.kpis if k.include_in_score]
        kpi_json = _make_kpi_json(kpi_ids, 7.0)
        r1 = compute_score(kpi_json, cfg, wcfg)
        r2 = compute_score(kpi_json, cfg, wcfg)
        assert r1 == r2

    def test_fact_kpi_plain_number_handled(self) -> None:
        """Plain numeric values (from stub) also work."""
        from app.config.kpi import KpiConfig, KpiItem, WeightsConfig
        from app.services.score import compute_score

        kpi = KpiItem(
            id="test_fact", label="Test", type="fact", weight=1.0,
            applies_to="baseline", include_in_score=True, anchors=[]
        )
        cfg = KpiConfig(kpis=[kpi])
        wcfg = WeightsConfig(normalization_rule="proportional", weights={})
        score, verdict = compute_score({"test_fact": 10}, cfg, wcfg)
        assert score == 100.0
        assert verdict == "+"

    def test_scale_kpi_rich_dict_value(self) -> None:
        from app.config.kpi import KpiConfig, KpiItem, WeightsConfig
        from app.services.score import compute_score

        kpi = KpiItem(
            id="greeting", label="Greeting", type="scale", weight=1.0,
            applies_to="baseline", include_in_score=True, anchors=[]
        )
        cfg = KpiConfig(kpis=[kpi])
        wcfg = WeightsConfig(normalization_rule="proportional", weights={})
        score, _ = compute_score(
            {"greeting": {"value": 5.0, "quote": "q", "comment": "c"}}, cfg, wcfg
        )
        assert abs(score - 50.0) < 0.01
