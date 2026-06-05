"""Scripts API — upload, versioning, active-version selection — M6-T2."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AdminRequired, AnyUserRequired
from app.db.models.script import ScriptModel, ScriptVerModel
from app.db.session import get_session
from app.services.scripts import parse_script_content

router = APIRouter(prefix="/api/scripts", tags=["scripts"])


class ScriptOut(BaseModel):
    id: uuid.UUID
    name: str
    is_active: bool
    active_version_id: uuid.UUID | None


class ScriptVerOut(BaseModel):
    id: uuid.UUID
    script_id: uuid.UUID
    version: int
    content: str
    kpi_binding: dict[str, Any] | None


class SetActiveVersionIn(BaseModel):
    version_id: uuid.UUID


async def _next_version_number(session: AsyncSession, script_id: uuid.UUID) -> int:
    result = await session.execute(
        select(ScriptVerModel)
        .where(ScriptVerModel.script_id == script_id)
        .order_by(ScriptVerModel.version.desc())
    )
    existing = result.scalar_one_or_none()
    return (existing.version + 1) if existing else 1


@router.get("", response_model=list[ScriptOut], dependencies=[AnyUserRequired])
async def list_scripts(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[ScriptOut]:
    result = await session.execute(
        select(ScriptModel).where(ScriptModel.is_active.is_(True)).order_by(ScriptModel.name)
    )
    return [ScriptOut.model_validate(r, from_attributes=True) for r in result.scalars().all()]


@router.get("/{script_id}", response_model=ScriptOut, dependencies=[AnyUserRequired])
async def get_script(
    script_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ScriptOut:
    s = await session.get(ScriptModel, script_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Script not found")
    return ScriptOut.model_validate(s, from_attributes=True)


@router.get(
    "/{script_id}/versions",
    response_model=list[ScriptVerOut],
    dependencies=[AnyUserRequired],
)
async def list_versions(
    script_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[ScriptVerOut]:
    s = await session.get(ScriptModel, script_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Script not found")
    result = await session.execute(
        select(ScriptVerModel)
        .where(ScriptVerModel.script_id == script_id)
        .order_by(ScriptVerModel.version)
    )
    return [ScriptVerOut.model_validate(r, from_attributes=True) for r in result.scalars().all()]


@router.post("", response_model=ScriptOut, status_code=201, dependencies=[AdminRequired])
async def create_script(
    name: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ScriptOut:
    raw = await file.read()
    try:
        content = parse_script_content(file.filename or "", raw)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    s = ScriptModel(id=uuid.uuid4(), name=name, is_active=True, active_version_id=None)
    session.add(s)
    await session.flush()

    ver = ScriptVerModel(
        id=uuid.uuid4(),
        script_id=s.id,
        version=1,
        content=content,
        kpi_binding=None,
    )
    session.add(ver)
    await session.flush()

    s.active_version_id = ver.id
    await session.commit()
    await session.refresh(s)
    return ScriptOut.model_validate(s, from_attributes=True)


@router.post(
    "/{script_id}/versions",
    response_model=ScriptVerOut,
    status_code=201,
    dependencies=[AdminRequired],
)
async def upload_version(
    script_id: uuid.UUID,
    file: Annotated[UploadFile, File()],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ScriptVerOut:
    s = await session.get(ScriptModel, script_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Script not found")

    raw = await file.read()
    try:
        content = parse_script_content(file.filename or "", raw)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    next_ver = await _next_version_number(session, script_id)
    ver = ScriptVerModel(
        id=uuid.uuid4(),
        script_id=script_id,
        version=next_ver,
        content=content,
        kpi_binding=None,
    )
    session.add(ver)
    await session.commit()
    await session.refresh(ver)
    return ScriptVerOut.model_validate(ver, from_attributes=True)


@router.patch(
    "/{script_id}/active-version",
    response_model=ScriptOut,
    dependencies=[AdminRequired],
)
async def set_active_version(
    script_id: uuid.UUID,
    body: SetActiveVersionIn,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ScriptOut:
    s = await session.get(ScriptModel, script_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Script not found")
    ver = await session.get(ScriptVerModel, body.version_id)
    if ver is None or ver.script_id != script_id:
        raise HTTPException(status_code=404, detail="Version not found for this script")
    s.active_version_id = body.version_id
    await session.commit()
    await session.refresh(s)
    return ScriptOut.model_validate(s, from_attributes=True)
