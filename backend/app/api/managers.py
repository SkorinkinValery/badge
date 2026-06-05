"""CRUD for /api/managers — M6-T1."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AdminRequired, AnyUserRequired
from app.db.models.manager import ManagerModel
from app.db.session import get_session

router = APIRouter(prefix="/api/managers", tags=["managers"])


class ManagerIn(BaseModel):
    full_name: str
    position: str
    device_id: str | None = None
    is_active: bool = True
    default_script_id: uuid.UUID | None = None


class ManagerPatchIn(BaseModel):
    full_name: str | None = None
    position: str | None = None
    device_id: str | None = None
    is_active: bool | None = None
    default_script_id: uuid.UUID | None = None


class ManagerOut(BaseModel):
    id: uuid.UUID
    full_name: str
    position: str
    device_id: str | None
    is_active: bool
    default_script_id: uuid.UUID | None


async def _check_device_id_unique(
    session: AsyncSession,
    device_id: str,
    exclude_id: uuid.UUID | None = None,
) -> None:
    stmt = select(ManagerModel).where(ManagerModel.device_id == device_id)
    if exclude_id is not None:
        stmt = stmt.where(ManagerModel.id != exclude_id)
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is not None:
        raise HTTPException(status_code=409, detail="device_id already in use")


@router.get("", response_model=list[ManagerOut], dependencies=[AnyUserRequired])
async def list_managers(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[ManagerOut]:
    result = await session.execute(select(ManagerModel).order_by(ManagerModel.full_name))
    return [ManagerOut.model_validate(r, from_attributes=True) for r in result.scalars().all()]


@router.get("/{manager_id}", response_model=ManagerOut, dependencies=[AnyUserRequired])
async def get_manager(
    manager_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ManagerOut:
    m = await session.get(ManagerModel, manager_id)
    if m is None:
        raise HTTPException(status_code=404, detail="Manager not found")
    return ManagerOut.model_validate(m, from_attributes=True)


@router.post("", response_model=ManagerOut, status_code=201, dependencies=[AdminRequired])
async def create_manager(
    body: ManagerIn,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ManagerOut:
    if body.device_id is not None:
        await _check_device_id_unique(session, body.device_id)
    m = ManagerModel(
        id=uuid.uuid4(),
        full_name=body.full_name,
        position=body.position,
        device_id=body.device_id,
        is_active=body.is_active,
        default_script_id=body.default_script_id,
    )
    session.add(m)
    await session.commit()
    await session.refresh(m)
    return ManagerOut.model_validate(m, from_attributes=True)


@router.patch("/{manager_id}", response_model=ManagerOut, dependencies=[AdminRequired])
async def update_manager(
    manager_id: uuid.UUID,
    body: ManagerPatchIn,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ManagerOut:
    m = await session.get(ManagerModel, manager_id)
    if m is None:
        raise HTTPException(status_code=404, detail="Manager not found")
    fields: dict[str, Any] = body.model_dump(exclude_unset=True)
    if "device_id" in fields and fields["device_id"] is not None:
        await _check_device_id_unique(session, fields["device_id"], exclude_id=manager_id)
    for key, val in fields.items():
        setattr(m, key, val)
    await session.commit()
    await session.refresh(m)
    return ManagerOut.model_validate(m, from_attributes=True)


@router.delete("/{manager_id}", response_model=ManagerOut, dependencies=[AdminRequired])
async def deactivate_manager(
    manager_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ManagerOut:
    """Soft-delete: sets is_active=False, preserves all recording history."""
    m = await session.get(ManagerModel, manager_id)
    if m is None:
        raise HTTPException(status_code=404, detail="Manager not found")
    m.is_active = False
    await session.commit()
    await session.refresh(m)
    return ManagerOut.model_validate(m, from_attributes=True)
