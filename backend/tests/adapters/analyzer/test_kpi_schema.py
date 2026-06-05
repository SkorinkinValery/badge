"""Unit tests for KpiResult dynamic schema — M4-T1."""

from __future__ import annotations

import pytest
from pydantic import ValidationError


class TestKpiResultSchemaBuildsFromConfig:
    def test_schema_importable(self) -> None:
        from app.adapters.analyzer.schema import build_kpi_result_model  # noqa: F401

    def test_schema_built_from_kpi_config(self) -> None:
        from app.adapters.analyzer.schema import build_kpi_result_model
        from app.config.kpi import load_kpi_config

        cfg = load_kpi_config()
        model = build_kpi_result_model(cfg)
        assert model is not None

    def test_schema_has_field_for_each_kpi(self) -> None:
        from app.adapters.analyzer.schema import build_kpi_result_model
        from app.config.kpi import load_kpi_config

        cfg = load_kpi_config()
        model = build_kpi_result_model(cfg)
        kpi_ids = {k.id for k in cfg.kpis}
        for field_name in model.model_fields:
            assert field_name in kpi_ids

    def test_schema_field_count_matches_kpis(self) -> None:
        from app.adapters.analyzer.schema import build_kpi_result_model
        from app.config.kpi import load_kpi_config

        cfg = load_kpi_config()
        model = build_kpi_result_model(cfg)
        assert len(model.model_fields) == len(cfg.kpis)


class TestKpiResultValidation:
    def test_valid_payload_parses(self) -> None:
        from app.adapters.analyzer.schema import KpiEntry, build_kpi_result_model
        from app.config.kpi import load_kpi_config

        cfg = load_kpi_config()
        model = build_kpi_result_model(cfg)
        payload = {kpi.id: {"value": 7.0, "quote": "цитата", "comment": "ok"} for kpi in cfg.kpis}
        instance = model.model_validate(payload)
        assert instance is not None

    def test_each_entry_has_value_quote_comment(self) -> None:
        from app.adapters.analyzer.schema import build_kpi_result_model
        from app.config.kpi import load_kpi_config

        cfg = load_kpi_config()
        model = build_kpi_result_model(cfg)
        payload = {kpi.id: {"value": 5.0, "quote": "q", "comment": "c"} for kpi in cfg.kpis}
        instance = model.model_validate(payload)
        entry = getattr(instance, cfg.kpis[0].id)
        assert hasattr(entry, "value")
        assert hasattr(entry, "quote")
        assert hasattr(entry, "comment")

    def test_missing_kpi_field_raises(self) -> None:
        from app.adapters.analyzer.schema import build_kpi_result_model
        from app.config.kpi import load_kpi_config

        cfg = load_kpi_config()
        model = build_kpi_result_model(cfg)
        # Provide all except the first KPI
        payload = {
            kpi.id: {"value": 7.0, "quote": "q", "comment": "c"}
            for kpi in cfg.kpis[1:]
        }
        with pytest.raises(ValidationError):
            model.model_validate(payload)

    def test_invalid_value_type_raises(self) -> None:
        from app.adapters.analyzer.schema import build_kpi_result_model
        from app.config.kpi import load_kpi_config

        cfg = load_kpi_config()
        model = build_kpi_result_model(cfg)
        payload = {
            kpi.id: {"value": "not_a_number", "quote": "q", "comment": "c"}
            for kpi in cfg.kpis
        }
        with pytest.raises(ValidationError):
            model.model_validate(payload)

    def test_value_out_of_range_raises(self) -> None:
        from app.adapters.analyzer.schema import build_kpi_result_model
        from app.config.kpi import load_kpi_config

        cfg = load_kpi_config()
        model = build_kpi_result_model(cfg)
        payload = {
            kpi.id: {"value": 999.0, "quote": "q", "comment": "c"}
            for kpi in cfg.kpis
        }
        with pytest.raises(ValidationError):
            model.model_validate(payload)


class TestKpiEntryModel:
    def test_kpi_entry_importable(self) -> None:
        from app.adapters.analyzer.schema import KpiEntry  # noqa: F401

    def test_fact_kpi_value_must_be_binary(self) -> None:
        """fact KPI: only 0 or 10 accepted."""
        from app.adapters.analyzer.schema import KpiEntry

        entry = KpiEntry(value=0.0, quote="q", comment="c", kpi_type="fact")
        assert entry.value == 0.0
        entry2 = KpiEntry(value=10.0, quote="q", comment="c", kpi_type="fact")
        assert entry2.value == 10.0

    def test_fact_kpi_invalid_value_raises(self) -> None:
        from app.adapters.analyzer.schema import KpiEntry

        with pytest.raises(ValidationError):
            KpiEntry(value=5.0, quote="q", comment="c", kpi_type="fact")

    def test_scale_kpi_accepts_range(self) -> None:
        from app.adapters.analyzer.schema import KpiEntry

        for v in [0.0, 3.0, 5.0, 7.0, 10.0]:
            entry = KpiEntry(value=v, quote="q", comment="c", kpi_type="scale")
            assert entry.value == v

    def test_json_schema_exportable(self) -> None:
        from app.adapters.analyzer.schema import build_kpi_result_model
        from app.config.kpi import load_kpi_config

        cfg = load_kpi_config()
        model = build_kpi_result_model(cfg)
        schema = model.model_json_schema()
        assert "properties" in schema
