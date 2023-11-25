"""src/core/db/repository/suspension.py"""
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db.db import get_session
from src.core.db.models import Suspension
from src.core.db.repository.base import ContentRepository


class SuspensionRepository(ContentRepository):
    """Репозиторий для работы с моделью Suspension."""

    def __init__(self, session: AsyncSession = Depends(get_session)) -> None:
        super().__init__(session, Suspension)

    async def get_all(self) -> list[Suspension]:
        """Возвращает все объекты модели из базы данных, отсортированные по времени."""
        objects = await self._session.execute(
            select(Suspension)
            .order_by(Suspension.datetime_start)
        )
        return objects.scalars().all()
