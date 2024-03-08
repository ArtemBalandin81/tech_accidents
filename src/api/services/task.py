"""src/api/services/task.py"""
from collections.abc import Sequence
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.constants import DISPLAY_TIME, FROM_TIME_NOW, TO_TIME_PERIOD
from src.api.schemas import SuspensionRequest
from src.core.db import get_session
from src.core.db.models import Suspension, Task, User
from src.core.db.repository.task import TaskRepository
from src.settings import settings


class TaskService:
    """Сервис для работы с моделью Task."""

    def __init__(
        self,
        task_repository: TaskRepository = Depends(),
        session: AsyncSession = Depends(get_session)
    ) -> None:
        self._repository: TaskRepository = task_repository
        self._session: AsyncSession = session

    async def actualize_object(
            self,
            task_id: int | None,
            in_object: dict,  # | SuspensionRequest,  # todo сервис не должен принимать pydantic: ждет схему или словарь
            user: User | int
    ):
        if in_object["task_start"] > in_object["deadline"]:
            raise HTTPException(status_code=422, detail="Check start_time > finish_time")
        if user is None:
            raise HTTPException(status_code=422, detail="Check USER is not NONE!")
        if type(user) is int:  # Проверяет, что пользователь не передается напрямую id
            in_object["user_id"] = user
        else:
            in_object["user_id"] = user.id
        task = Task(**in_object)
        if task_id is None:  # если task_id не передан - создаем, иначе - правим!
            return await self._repository.create(task)
        await self.get(task_id)  # проверяем, что объект для правки существует!
        return await self._repository.update(task_id, task)


    async def get(self, task_id: int) -> Task:
        return await self._repository.get(task_id)


    async def get_all(self) -> list[any]:
        return await self._repository.get_all()


    async def get_all_for_period_time(
            self,
            task_start: datetime = TO_TIME_PERIOD,
            deadline: datetime = FROM_TIME_NOW
    ) -> Sequence[Task]:
        return await self._repository.get_all_for_period_time(task_start, deadline)  # todo проверь!


    async def get_last_task_id(self, user_id: int) -> int:
        if user_id is None:
            return await self._repository.get_last_id()
        else:
            return await self._repository.get_last_id_for_user(user_id)


    async def get_last_task_time(self, user_id: int) -> datetime:
        if user_id is None:
            last_task = await self._repository.get(await self._repository.get_last_id())
        else:
            last_task = await self._repository.get(await self.get_last_task_id(user_id))
        return last_task.task_start


    async def get_tasks_for_user(self, user_id: int) -> Sequence[any]:
        return await self._repository.get_tasks_for_user(user_id)


    async def get_taskss_for_period_for_user(
        self,
        user_id: int,
        task_start: datetime = TO_TIME_PERIOD,
        deadline: datetime = FROM_TIME_NOW
    ) -> Sequence[any]:
        return await self._repository.get_tasks_for_period_for_user(user_id, task_start, deadline)


    async def sum_tasks_time_for_period(
            self,
            user_id: int,
            task_start: datetime = TO_TIME_PERIOD,
            deadline: datetime = FROM_TIME_NOW
    ) -> int:
        if user_id is None:
            total_time_tasks = await self._repository.sum_time_for_period(task_start, deadline)
        else:
            total_time_tasks = await self._repository.sum_time_for_period_for_user(
                user_id, task_start, deadline
            )
        if total_time_tasks is None:
            return 0
        return round(total_time_tasks * DISPLAY_TIME)


    async def task_max_time_for_period(
            self,
            user_id: int,
            task_start: datetime = TO_TIME_PERIOD,
            deadline: datetime = FROM_TIME_NOW
    ) -> int:
        if user_id is None:
            max_time_for_period = await self._repository.task_max_time_for_period(
                task_start, deadline
            )
        else:
            max_time_for_period = await self._repository.task_max_time_for_period_for_user(
                user_id, task_start, deadline
            )
        if max_time_for_period is None:
            return 0
        return round(max_time_for_period * DISPLAY_TIME)


    async def remove(self, task_id: int) -> None:
        task = await self._repository.get(task_id)
        return await self._repository.remove(task)
