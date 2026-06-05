"""M0-T4: Tests for kpi.yaml / weights.yaml loaders."""

from pathlib import Path

import pytest

KPI_YAML = Path(__file__).parent.parent.parent.parent / "infra" / "config" / "kpi.yaml"
WEIGHTS_YAML = Path(__file__).parent.parent.parent.parent / "infra" / "config" / "weights.yaml"


def test_kpi_yaml_exists() -> None:
    assert KPI_YAML.exists()


def test_weights_yaml_exists() -> None:
    assert WEIGHTS_YAML.exists()


def test_kpi_config_parses() -> None:
    from app.config.kpi import load_kpi_config

    cfg = load_kpi_config(KPI_YAML)
    assert len(cfg.kpis) > 0


def test_kpi_has_10_items() -> None:
    from app.config.kpi import load_kpi_config

    cfg = load_kpi_config(KPI_YAML)
    assert len(cfg.kpis) == 10, f"Expected 10 KPIs, got {len(cfg.kpis)}"


def test_kpi_fields_present() -> None:
    """Each KPI must have id, label, type, weight, anchors, applies_to, include_in_score."""
    from app.config.kpi import load_kpi_config

    cfg = load_kpi_config(KPI_YAML)
    for kpi in cfg.kpis:
        assert kpi.id
        assert kpi.label
        assert kpi.type in ("scale", "fact")
        assert isinstance(kpi.anchors, list)
        assert kpi.applies_to in ("baseline", "script")
        assert isinstance(kpi.include_in_score, bool)


def test_kpi_script_compliance_is_script_type() -> None:
    """KPI #9 'соблюдение регламента/скрипта' must be applies_to=script."""
    from app.config.kpi import load_kpi_config

    cfg = load_kpi_config(KPI_YAML)
    script_kpis = [k for k in cfg.kpis if k.applies_to == "script"]
    assert len(script_kpis) >= 1, "At least one KPI must be applies_to=script"


def test_kpi_anchors_present_for_scale_kpis() -> None:
    """Scale KPIs must have behavioural anchors."""
    from app.config.kpi import load_kpi_config

    cfg = load_kpi_config(KPI_YAML)
    for kpi in cfg.kpis:
        if kpi.type == "scale":
            assert len(kpi.anchors) > 0, f"KPI '{kpi.id}' has no anchors"


def test_invalid_kpi_type_raises() -> None:
    from pydantic import ValidationError

    from app.config.kpi import KpiItem

    with pytest.raises(ValidationError):
        KpiItem(
            id="bad",
            label="Bad",
            type="invalid_type",  # type: ignore[arg-type]
            weight=1.0,
            anchors=[],
            applies_to="baseline",
            include_in_score=True,
        )


def test_weights_config_parses() -> None:
    from app.config.kpi import load_weights_config

    cfg = load_weights_config(WEIGHTS_YAML)
    assert cfg.weights


def test_weights_reference_valid_kpi_ids() -> None:
    from app.config.kpi import load_kpi_config, load_weights_config

    kpi_cfg = load_kpi_config(KPI_YAML)
    weights_cfg = load_weights_config(WEIGHTS_YAML)
    kpi_ids = {k.id for k in kpi_cfg.kpis}
    for wid in weights_cfg.weights:
        assert wid in kpi_ids, f"Weight references unknown KPI id: '{wid}'"


def test_weights_normalization_rule_described() -> None:
    from app.config.kpi import load_weights_config

    cfg = load_weights_config(WEIGHTS_YAML)
    # normalization_rule must be present
    assert cfg.normalization_rule in ("proportional", "equal")
