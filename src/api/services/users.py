"""src/api/services/users.py"""
import json
from typing import Sequence

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.db import get_session
from src.core.db.models import User
from src.core.db.repository.users import UsersRepository


class UsersService:
    """Сервис для работы с моделью User."""

    def __init__(
        self,
        users_repository: UsersRepository = Depends(),
        session: AsyncSession = Depends(get_session)
    ) -> None:
        self._repository: UsersRepository = users_repository
        self._session: AsyncSession = session

    async def get(self, user_id: int) -> User:
        return await self._repository.get(user_id)

    async def get_by_email(self, _email: str) -> User:
        return await self._repository.get_by_email(_email)

    async def get_all(self) -> Sequence[User]:
        return await self._repository.get_all()

    async def get_all_active(self) -> str:
        active_users = await self._repository.get_all_active()
        users_dict = {}
        for user in active_users:
            users_dict[user.id] = user.email
        return json.dumps(users_dict)
