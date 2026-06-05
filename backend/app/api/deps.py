"""FastAPI dependencies: JWT auth, role guards."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer

from app.services.auth import UserRole, decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def _settings(request: Request) -> Any:
    return request.app.state.settings


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    request: Request,
) -> dict[str, str]:
    settings = request.app.state.settings
    try:
        payload = decode_token(token, settings.jwt_secret)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc
    sub = payload.get("sub")
    role = payload.get("role")
    if not sub or not role:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    return {"sub": str(sub), "role": str(role)}


CurrentUser = Annotated[dict[str, str], Depends(get_current_user)]


def require_role(*roles: UserRole):  # type: ignore[no-untyped-def]
    async def _check(user: CurrentUser) -> dict[str, str]:
        if user["role"] not in [r.value for r in roles]:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return user
    return _check


AdminRequired = Depends(require_role(UserRole.ADMIN))
AnyUserRequired = Depends(get_current_user)
