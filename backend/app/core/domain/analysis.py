"""Analysis domain entity."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

from app.core.domain.enums import AnalysisMode, Verdict


@dataclass(config=ConfigDict(frozen=True))
class Analysis:
    id: uuid.UUID
    recording_id: uuid.UUID
    summary: str
    kpi_json: dict[str, Any]
    score: float
    verdict: Verdict
    mode: AnalysisMode
    script_version_id: uuid.UUID | None
    weights_version: str
