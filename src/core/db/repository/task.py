"""src/core/db/repository/task.py"""
from collections.abc import Sequence
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db.db import get_session
from src.core.db.models import Task
from src.core.db.repository.base import ContentRepository


class TaskRepository(ContentRepository):
    """Репозиторий для работы с моделью Task."""

    def __init__(self, session: AsyncSession = Depends(get_session)) -> None:
        super().__init__(session, Task)

    async def get_all(self) -> Sequence[Task]:
        """Возвращает все задачи из базы данных, отсортированные по времени."""
        objects = await self._session.scalars(
            select(Task)
            .order_by(Task.task_start.desc())
        )
        return objects.all()

    async def get_all_opened(self) -> Sequence[Task]:
        """Возвращает активные задачи из базы данных, отсортированные по времени."""
        objects = await self._session.scalars(
            select(Task)
            .where(Task.is_archived == 0)
            .order_by(Task.task_start.desc())
        )
        return objects.all()

    async def get_tasks_ordered(self, user_id: int, limit: int = 3, offset: int = 0) -> Sequence[Task]:
        """Получить список задач, выставленных пользователем."""
        tasks_ordered_for_user = await self._session.scalars(
            select(Task)
            .where(Task.user_id == user_id)
            .where(Task.is_archived == 0)
            # .limit(limit)  # todo реализовать пагинацию
            # .offset(offset)
            .order_by(Task.deadline.asc())
        )
        return tasks_ordered_for_user.all()

    async def get_tasks_todo(self, user_id: int, limit: int = 3, offset: int = 0) -> Sequence[Task]:
        """Получить список задач, выставленных пользователю."""
        tasks_todo = await self._session.scalars(
            select(Task)
            .where(Task.executor == user_id)
            .where(Task.is_archived == 0)
            # .limit(limit)  # todo реализовать пагинацию
            # .offset(offset)
            .order_by(Task.deadline.asc())
        )
        return tasks_todo.all()
