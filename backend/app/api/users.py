"""CRUD /api/admin/users — admin-only user management (B5)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AdminRequired
from app.db.models.user import UserModel
from app.db.repositories.user_repo import UserRepository
from app.db.session import get_session
from app.services.auth import UserRole, hash_password

router = APIRouter(prefix="/api/admin/users", tags=["admin-users"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class UserCreateIn(BaseModel):
    login: str
    password: str
    role: UserRole = UserRole.VIEWER


class UserOut(BaseModel):
    id: uuid.UUID
    login: str
    role: str
    is_active: bool


class UserPatchIn(BaseModel):
    is_active: bool | None = None
    role: UserRole | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=list[UserOut], dependencies=[AdminRequired])
async def list_users(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[UserOut]:
    repo = UserRepository(session)
    users = await repo.list_users()
    return [UserOut.model_validate(u, from_attributes=True) for u in users]


@router.post("", response_model=UserOut, status_code=201, dependencies=[AdminRequired])
async def create_user(
    body: UserCreateIn,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserOut:
    repo = UserRepository(session)
    existing = await repo.find_by_login(body.login)
    if existing is not None:
        raise HTTPException(status_code=409, detail="Login already in use")
    user = await repo.create_user(
        login=body.login,
        password_hash=hash_password(body.password),
        role=body.role.value,
    )
    await session.commit()
    await session.refresh(user)
    return UserOut.model_validate(user, from_attributes=True)


@router.patch("/{user_id}", response_model=UserOut, dependencies=[AdminRequired])
async def patch_user(
    user_id: uuid.UUID,
    body: UserPatchIn,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserOut:
    user = await session.get(UserModel, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.role is not None:
        user.role = body.role.value
    await session.commit()
    await session.refresh(user)
    return UserOut.model_validate(user, from_attributes=True)


@router.delete("/{user_id}", status_code=204, dependencies=[AdminRequired])
async def delete_user(
    user_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    repo = UserRepository(session)
    deleted = await repo.delete(user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")
    await session.commit()
