"""Unit tests for resolve_analysis_mode — M6-T3."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.anyio
async def test_baseline_mode_when_manager_has_no_script() -> None:
    from app.services.process import resolve_analysis_mode

    mock_manager = MagicMock()
    mock_manager.default_script_id = None

    session = AsyncMock()
    session.get = AsyncMock(return_value=mock_manager)

    mode, version_id, content = await resolve_analysis_mode(uuid.uuid4(), session)

    assert mode == "baseline"
    assert version_id is None
    assert content is None


@pytest.mark.anyio
async def test_baseline_mode_when_manager_not_found() -> None:
    from app.services.process import resolve_analysis_mode

    session = AsyncMock()
    session.get = AsyncMock(return_value=None)

    mode, version_id, content = await resolve_analysis_mode(uuid.uuid4(), session)

    assert mode == "baseline"
    assert version_id is None
    assert content is None


@pytest.mark.anyio
async def test_script_mode_when_manager_has_active_script() -> None:
    from app.db.models.manager import ManagerModel
    from app.db.models.script import ScriptModel, ScriptVerModel
    from app.services.process import resolve_analysis_mode

    script_ver_id = uuid.uuid4()
    script_id = uuid.uuid4()
    manager_id = uuid.uuid4()

    mock_manager = MagicMock(spec=ManagerModel)
    mock_manager.default_script_id = script_id

    mock_script = MagicMock(spec=ScriptModel)
    mock_script.active_version_id = script_ver_id

    mock_ver = MagicMock(spec=ScriptVerModel)
    mock_ver.id = script_ver_id
    mock_ver.content = "1. Greet customer\n2. Identify needs"

    session = AsyncMock()
    session.get = AsyncMock(
        side_effect=lambda model, pk: {
            (ManagerModel, manager_id): mock_manager,
            (ScriptModel, script_id): mock_script,
            (ScriptVerModel, script_ver_id): mock_ver,
        }.get((model, pk))
    )

    mode, version_id, content = await resolve_analysis_mode(manager_id, session)

    assert mode == "script"
    assert version_id == script_ver_id
    assert content == "1. Greet customer\n2. Identify needs"


@pytest.mark.anyio
async def test_baseline_mode_when_script_has_no_active_version() -> None:
    from app.db.models.manager import ManagerModel
    from app.db.models.script import ScriptModel
    from app.services.process import resolve_analysis_mode

    script_id = uuid.uuid4()
    manager_id = uuid.uuid4()

    mock_manager = MagicMock(spec=ManagerModel)
    mock_manager.default_script_id = script_id

    mock_script = MagicMock(spec=ScriptModel)
    mock_script.active_version_id = None

    session = AsyncMock()
    session.get = AsyncMock(
        side_effect=lambda model, pk: {
            (ManagerModel, manager_id): mock_manager,
            (ScriptModel, script_id): mock_script,
        }.get((model, pk))
    )

    mode, version_id, content = await resolve_analysis_mode(manager_id, session)

    assert mode == "baseline"
    assert version_id is None
    assert content is None


@pytest.mark.anyio
async def test_script_version_id_is_recorded_for_reproducibility() -> None:
    """script_version_id in result enables future analysis replay."""
    from app.db.models.manager import ManagerModel
    from app.db.models.script import ScriptModel, ScriptVerModel
    from app.services.process import resolve_analysis_mode

    script_ver_id = uuid.uuid4()
    script_id = uuid.uuid4()
    manager_id = uuid.uuid4()

    mock_manager = MagicMock(spec=ManagerModel)
    mock_manager.default_script_id = script_id
    mock_script = MagicMock(spec=ScriptModel)
    mock_script.active_version_id = script_ver_id
    mock_ver = MagicMock(spec=ScriptVerModel)
    mock_ver.id = script_ver_id
    mock_ver.content = "Script content"

    session = AsyncMock()
    session.get = AsyncMock(
        side_effect=lambda model, pk: {
            (ManagerModel, manager_id): mock_manager,
            (ScriptModel, script_id): mock_script,
            (ScriptVerModel, script_ver_id): mock_ver,
        }.get((model, pk))
    )

    _, returned_version_id, _ = await resolve_analysis_mode(manager_id, session)
    assert returned_version_id == script_ver_id
