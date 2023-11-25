"""src/core/db/repository/user.py"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db.db import get_session
from src.core.db.models import User
from src.core.db.repository.base import ContentRepository


class UsersRepository(ContentRepository):
    """Репозиторий для работы с моделью User."""

    def __init__(self, session: AsyncSession = Depends(get_session)) -> None:
        super().__init__(session, User)
