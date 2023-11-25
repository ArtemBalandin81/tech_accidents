"""src/api/user_service.py"""
from datetime import datetime
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db import get_session
from src.core.db.models import User
from src.core.db.repository import UsersRepository


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
