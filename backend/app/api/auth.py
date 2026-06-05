"""POST /api/auth/login — JWT OAuth2 password flow."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from app.config.settings import Settings, get_settings
from app.services.auth import create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=TokenOut)
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenOut:
    # Admin credentials come from env; DB-based multi-user lookup added in T3
    valid = (
        form.username == settings.admin_login
        and form.password == settings.admin_password
    )
    if not valid:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(
        sub=form.username,
        role="admin",
        secret=settings.jwt_secret,
        expire_minutes=settings.jwt_expire_minutes,
    )
    return TokenOut(access_token=token)
