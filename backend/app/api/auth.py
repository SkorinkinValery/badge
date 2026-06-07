"""POST /api/auth/login — JWT OAuth2 password flow (DB-backed since B2)."""

from __future__ import annotations

import collections
import time
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings, get_settings
from app.db.repositories.user_repo import UserRepository
from app.db.session import get_session
from app.services.auth import create_access_token, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Simple in-memory rate limiter: max 5 attempts per IP per 60 seconds.
# State lives on app.state (per-app, not module-global) so each create_app()
# instance — including ones created per-test — starts with a clean slate.
_RATE_LIMIT_MAX = 5
_RATE_LIMIT_WINDOW = 60.0


def _check_rate_limit(app_state: Any, ip: str) -> None:
    attempts_by_ip: dict[str, collections.deque[float]] | None = getattr(
        app_state, "login_attempts", None
    )
    if attempts_by_ip is None:
        attempts_by_ip = collections.defaultdict(collections.deque)
        app_state.login_attempts = attempts_by_ip

    now = time.monotonic()
    attempts = attempts_by_ip[ip]
    # Remove timestamps outside the window
    while attempts and now - attempts[0] > _RATE_LIMIT_WINDOW:
        attempts.popleft()
    if len(attempts) >= _RATE_LIMIT_MAX:
        raise HTTPException(status_code=429, detail="Too many login attempts, try again later")
    attempts.append(now)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=TokenOut)
async def login(
    request: Request,
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenOut:
    _check_rate_limit(request.app.state, request.client.host if request.client else "unknown")
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
