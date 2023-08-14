"""src/api/services/suspension.py"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.services.base import ContentService
from src.core.db import get_session
from src.core.db.models import Suspension
from src.core.db.repository.suspension import SuspensionRepository


class SuspensionService(ContentService):
    """Сервис для работы с моделью Suspension."""

    def __init__(
        self, suspension_repository: SuspensionRepository = Depends(), session: AsyncSession = Depends(get_session)
    ) -> None:
        super().__init__(suspension_repository, session)

    # async def get_tasks_for_user(self, user_id: int) -> list[Task]:
    #     return await self._repository.get_tasks_for_user(user_id)
    #
    # async def get_user_task_id(self, task_id: int) -> list[Task]:
    #     return await self._repository.get_user_task_id(task_id)
    #
    # async def get_user_tasks_ids(self, ids: list[int]) -> list[Task]:
    #     return await self._repository.get_user_tasks_ids(ids)
