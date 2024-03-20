"""src/api/services/users.py"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Sequence

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
