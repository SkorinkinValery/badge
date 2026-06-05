"""Script domain entity."""

from __future__ import annotations

import uuid

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass


@dataclass(config=ConfigDict(frozen=True))
class Script:
    id: uuid.UUID
    name: str
    is_active: bool
