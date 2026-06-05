"""KPI and weights config loader.

All KPI definitions and scoring weights come from kpi.yaml / weights.yaml.
No KPI hardcoding in application code — this module is the single source of truth.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, field_validator

# Default paths — can be overridden in tests or deployment
_DEFAULT_KPI_PATH = (
    Path(__file__).parent.parent.parent.parent / "infra" / "config" / "kpi.yaml"
)
_DEFAULT_WEIGHTS_PATH = (
    Path(__file__).parent.parent.parent.parent / "infra" / "config" / "weights.yaml"
)

KpiType = Literal["scale", "fact"]
AppliesTo = Literal["baseline", "script"]


class KpiItem(BaseModel):
    """Single KPI definition with behavioural anchors."""

    id: str
    label: str
    type: KpiType
    weight: float
    anchors: list[str]
    applies_to: AppliesTo
    include_in_score: bool

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in ("scale", "fact"):
            raise ValueError(f"KPI type must be 'scale' or 'fact', got: {v!r}")
        return v

    @field_validator("applies_to")
    @classmethod
    def validate_applies_to(cls, v: str) -> str:
        if v not in ("baseline", "script"):
            raise ValueError(f"applies_to must be 'baseline' or 'script', got: {v!r}")
        return v


class KpiConfig(BaseModel):
    """Container for the full KPI list loaded from kpi.yaml."""

    kpis: list[KpiItem]


class WeightsConfig(BaseModel):
    """Scoring weights and normalization rule loaded from weights.yaml."""

    normalization_rule: Literal["proportional", "equal"]
    weights: dict[str, float]

    @field_validator("weights")
    @classmethod
    def validate_weights_positive(cls, v: dict[str, float]) -> dict[str, float]:
        for k, w in v.items():
            if w < 0:
                raise ValueError(f"Weight for '{k}' must be non-negative, got: {w}")
        return v


def load_kpi_config(kpi_path: Path = _DEFAULT_KPI_PATH) -> KpiConfig:
    """Load and validate KPI definitions from kpi.yaml."""
    with open(kpi_path) as f:
        raw: dict[object, object] = yaml.safe_load(f) or {}
    return KpiConfig.model_validate(raw)


def load_weights_config(weights_path: Path = _DEFAULT_WEIGHTS_PATH) -> WeightsConfig:
    """Load and validate weights from weights.yaml."""
    with open(weights_path) as f:
        raw: dict[object, object] = yaml.safe_load(f) or {}

    # Validate that weights reference valid KPI ids (done at call site with load_kpi_config)
    return WeightsConfig.model_validate(raw)


def validate_weights_consistency(kpi_cfg: KpiConfig, weights_cfg: WeightsConfig) -> None:
    """Raise ValueError if weights reference unknown KPI ids."""
    kpi_ids = {k.id for k in kpi_cfg.kpis}
    unknown = set(weights_cfg.weights.keys()) - kpi_ids
    if unknown:
        raise ValueError(f"Weights reference unknown KPI ids: {unknown!r}")
