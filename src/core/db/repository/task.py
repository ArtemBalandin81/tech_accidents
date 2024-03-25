"""src/core/db/repository/task.py"""
from collections.abc import Sequence
from datetime import datetime
from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db.db import get_session
from src.core.db.models import Task, User
from src.core.db.repository.base import ContentRepository


class TaskRepository(ContentRepository):
    """Репозиторий для работы с моделью Task."""

    def __init__(self, session: AsyncSession = Depends(get_session)) -> None:
        super().__init__(session, Task)

    # async def count_for_period_for_user(
    #         self,
    #         executor: int,
    #         task_start: datetime,
    #         deadline: datetime,
    #
    # ) -> int:
    #     """Считает количество задач за указанные период для исполнителя."""
    #     return await self._session.scalar(
    #         select(func.count(Task.task_start))
    #         .where(Task.executor == executor)
    #         .where(Task.task_start >= task_start)
    #         .where(Task.task_start <= deadline)
    #     )

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

    # async def get_last_id_for_user(self, user_id: int) -> int:
    #     """Возвращает последнюю по времени задачу для заказчика."""
    #     return await self._session.scalar(
    #         select(Task.id)
    #         .where(Task.user_id == user_id)
    #         .order_by(Task.id.desc())
    #     )

    async def get_tasks_ordered(self, user_id: int, limit: int = 3, offset: int = 0) -> Sequence[Task]:
        """Получить список задач, выставленных пользователем."""
        tasks_ordered_for_user = await self._session.scalars(
            select(Task)
            .where(Task.user_id == user_id)
            .where(Task.is_archived == 0)
            # .limit(limit)  # todo реализовать пагинацию
            # .offset(offset)
            .order_by(Task.task_start.desc())
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

    # async def get_tasks_for_period_for_user(
    #         self,
    #         user_id: int,
    #         task_start: datetime,
    #         deadline: datetime
    # ) -> Sequence[Task]:
    #     """Получить список задач заказчика за выбранный период времени."""
    #     tasks_for_user_for_period = await self._session.scalars(
    #         select(Task)
    #         .where(Task.user_id == user_id)
    #         .where(Task.task_start >= task_start)
    #         .where(Task.deadline <= deadline)
    #         .order_by(Task.task_start.desc())
    #         .order_by(Task.task_start.desc())
    #     )
    #     return tasks_for_user_for_period.all()
    #
    # async def task_max_time_for_period_for_user(
    #         self,
    #         user_id: int,
    #         task_start: datetime,
    #         deadline: datetime
    # ) -> int:
    #     """Считает максимальную разницу между началом и концом за указанный период для заказчика."""
    #     return await self._session.scalar(
    #         select(func.max(func.julianday(Task.deadline) - func.julianday(Task.task_start)))
    #         .where(Task.user_id == user_id)
    #         .where(Task.task_start >= task_start)
    #         .where(Task.deadline <= deadline)
    #     )
    #
    # async def sum_time_for_period_for_user(
    #         self,
    #         user_id: int,
    #         task_start: datetime,
    #         deadline: datetime,
    #
    # ) -> int:
    #     """Считает время в днях за указанный период для заказчика."""
    #     return await self._session.scalar(
    #         select(func.sum(func.julianday(Task.deadline) - func.julianday(Task.task_start)))
    #         .where(Task.user_id == user_id)
    #         .where(Task.task_start >= task_start)
    #         .where(Task.deadline <= deadline)
    #     )
