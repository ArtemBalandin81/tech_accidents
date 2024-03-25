"""src/core/db/repository/user.py"""
from typing import Sequence

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db.db import get_session
from src.core.db.models import User
from src.core.db.repository.base import ContentRepository
from src.core.exceptions import NotFoundException


class UsersRepository(ContentRepository):
    """Репозиторий для работы с моделью User."""

    def __init__(self, session: AsyncSession = Depends(get_session)) -> None:
        super().__init__(session, User)

    async def get_or_none_email(self, _email: str) -> User | None:
        """Получает из базы объект модели по email. В случае отсутствия возвращает None."""
        return await self._session.scalar(select(User).where(User.email == _email))

    async def get_by_email(self, _email: str) -> User:
        """Получает объект модели по email. В случае отсутствия объекта бросает ошибку."""
        db_obj = await self.get_or_none_email(_email)
        if db_obj is None:
            raise NotFoundException(object_name=User.__name__, object_id=0)
        return db_obj

    async def get_all_active(self,) -> Sequence[User]:
        """Возвращает всех активных пользователей из базы данных."""
        objects = await self._session.scalars(select(User).where(User.is_active == 1))
        return objects.all()
