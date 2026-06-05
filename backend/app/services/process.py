"""Analysis mode resolver — M6-T3.

Determines whether a recording should use 'script' or 'baseline' analysis mode
based on whether the manager has an active script version assigned.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.manager import ManagerModel
from app.db.models.script import ScriptModel, ScriptVerModel


async def resolve_analysis_mode(
    manager_id: uuid.UUID,
    session: AsyncSession,
) -> tuple[str, uuid.UUID | None, str | None]:
    """Return (mode, script_version_id, script_content) for a manager.

    Returns 'script' mode only when the manager has a default_script_id pointing
    to a script that has an active version — guaranteeing content is available for
    the prompt. Falls back to 'baseline' in all other cases.
    """
    manager = await session.get(ManagerModel, manager_id)
    if manager is None or manager.default_script_id is None:
        return "baseline", None, None

    script = await session.get(ScriptModel, manager.default_script_id)
    if script is None or script.active_version_id is None:
        return "baseline", None, None

    script_ver = await session.get(ScriptVerModel, script.active_version_id)
    if script_ver is None:
        return "baseline", None, None

    return "script", script_ver.id, script_ver.content
