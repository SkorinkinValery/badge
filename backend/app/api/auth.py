"""POST /api/auth/login — JWT OAuth2 password flow (DB-backed since B2)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings, get_settings
from app.db.repositories.user_repo import UserRepository
from app.db.session import get_session
from app.services.auth import create_access_token, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=TokenOut)
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenOut:
    repo = UserRepository(session)
    user = await repo.find_by_login(form.username)

    if user is None or not user.is_active or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(
        sub=user.login,
        role=user.role,
        secret=settings.jwt_secret,
        expire_minutes=settings.jwt_expire_minutes,
    )
    return TokenOut(access_token=token)
