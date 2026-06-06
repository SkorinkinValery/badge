"""User repository — async, satisfies services.auth.AsyncUserRepo protocol."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import UserModel


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_login(self, login: str) -> UserModel | None:
        result = await self._session.execute(
            select(UserModel).where(UserModel.login == login)
        )
        return result.scalar_one_or_none()

    async def create_user(
        self,
        login: str,
        password_hash: str,
        role: str,
    ) -> UserModel:
        user = UserModel(
            id=uuid.uuid4(),
            login=login,
            password_hash=password_hash,
            role=role,
            is_active=True,
        )
        self._session.add(user)
        await self._session.flush()
        return user

    async def list_users(self) -> list[UserModel]:
        result = await self._session.execute(
            select(UserModel).order_by(UserModel.login)
        )
        return list(result.scalars().all())

    async def set_active(self, user_id: uuid.UUID, is_active: bool) -> UserModel | None:
        user = await self._session.get(UserModel, user_id)
        if user is None:
            return None
        user.is_active = is_active
        await self._session.flush()
        return user

    async def delete(self, user_id: uuid.UUID) -> bool:
        """Hard-delete a user record. Returns True if deleted, False if not found."""
        user = await self._session.get(UserModel, user_id)
        if user is None:
            return False
        await self._session.delete(user)
        await self._session.flush()
        return True
