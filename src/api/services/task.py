"""src/api/services/task.py"""
from collections.abc import Sequence

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.db import get_session
from src.core.db.models import Task, User
from src.core.db.repository.task import TaskRepository
from src.core.db.repository.users import UsersRepository
from src.core.enums import TechProcess


class TaskService:
    """Сервис для работы с моделью Task."""

    def __init__(
        self,
        task_repository: TaskRepository = Depends(),
        users_repository: UsersRepository = Depends(),
        session: AsyncSession = Depends(get_session)
    ) -> None:
        self._repository: TaskRepository = task_repository
        self._users_repository: UsersRepository = users_repository
        self._session: AsyncSession = session

    async def change_schema_response(
            self,
            task: Task,
    ) -> dict:
        """Изменяет и добавляет поля в словарь в целях наглядного представления в ответе api."""
        user = await self._users_repository.get(task.user_id)
        executor = await self._users_repository.get(task.executor)  # todo поменять на executor_id
        task_to_dict = task.__dict__
        task_to_dict["user_email"] = user.email
        task_to_dict["executor_email"] = executor.email
        task_to_dict["business_process"] = TechProcess(str(task.tech_process)).name  # str требуется enum-классу
        return task_to_dict

    async def perform_changed_schema(  # todo сделать универсальный сервис под разные модели и перенести в base
            self,
            tasks: Task | Sequence[Task],
    ) -> Sequence[dict]:
        """Готовит список словарей для отправки в api."""
        list_changed_response = []
        if type(tasks) is not list:
            list_changed_response.append(await self.change_schema_response(tasks))
        else:
            for task in tasks:
                list_changed_response.append(await self.change_schema_response(task))
        return list_changed_response

    async def actualize_object(
            self,
            task_id: int | None,
            in_object: dict,
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

    async def get_all(self) -> Sequence[any]:
        return await self._repository.get_all()

    async def get_all_opened(self) -> Sequence[any]:
        return await self._repository.get_all_opened()

    async def get_tasks_ordered(self, user_id: int) -> Sequence[any]:
        return await self._repository.get_tasks_ordered(user_id)

    async def get_my_tasks_todo(self, user_id: int) -> Sequence[any]:
        return await self._repository.get_tasks_todo(user_id)

    async def remove(self, task_id: int) -> None:
        task = await self._repository.get(task_id)
        return await self._repository.remove(task)
