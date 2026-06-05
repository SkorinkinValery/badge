"""Manager domain entity."""

from __future__ import annotations

import uuid

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass


@dataclass(config=ConfigDict(frozen=True))
class Manager:
    id: uuid.UUID
    full_name: str
    position: str
    device_id: str | None
    is_active: bool
    default_script_id: uuid.UUID | None
