"""src/api/services/task.py"""
from collections.abc import Sequence
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from src.api.constants import *
from src.api.schema import TaskCreate
from src.core.db import get_session
from src.core.db.models import Task, TasksFiles, User, FileAttached
from src.core.db.repository.file_attached import FileRepository
from src.core.db.repository.task import TaskRepository
from src.core.db.repository.users import UsersRepository
from src.core.enums import TechProcess

log = structlog.get_logger()

class TaskService:
    """Сервис для работы с моделью Task."""

    def __init__(
        self,
        file_repository: FileRepository = Depends(),
        task_repository: TaskRepository = Depends(),
        users_repository: UsersRepository = Depends(),
        session: AsyncSession = Depends(get_session)
    ) -> None:
        self._file_repository: FileRepository = file_repository
        self._repository: TaskRepository = task_repository
        self._users_repository: UsersRepository = users_repository
        self._session: AsyncSession = session

    async def change_schema_response(self, task: Task) -> dict:
        """Изменяет и добавляет поля в словарь в целях наглядного представления в ответе api."""
        user = await self._users_repository.get(task.user_id)
        executor = await self._users_repository.get(task.executor)  # todo поменять на executor_id: в модели и тут
        task_to_dict = task.__dict__
        task_to_dict["user_email"] = user.email
        task_to_dict["executor_email"] = executor.email
        task_to_dict["business_process"] = TechProcess(str(task.tech_process)).name  # str требуется enum-классу
        task_to_dict["extra_files"] = []
        return task_to_dict

    async def validate_files_exist_and_get_file_names(  # todo сделать универсальный сервис
            self,
            task_id: int,
    ) -> Sequence[str] | None:
        """Отдает имена файлов из таблицы TasksFiles, если они записаны в БД и запись (m-t-m) им соответствует."""
        file_ids: Sequence[int] = await self.get_file_ids_from_task(task_id)
        # file_names: Sequence[str] = await self.get_file_names_from_task(task_id)
        file_names_and_ids: tuple[list[str], list[int]] = await self.get_file_names_and_ids_from_task(task_id)
        if len(file_ids) != len(file_names_and_ids[0]):
            tasks_files_mismatch = "{}{}{}{}{}".format(
                TASK, task_id, TASKS_FILES_MISMATCH, file_ids, file_names_and_ids[0]
            )
            await log.aerror(tasks_files_mismatch)
            raise HTTPException(status_code=206, detail=tasks_files_mismatch)
        # await log.ainfo("{}{}{}{}{}".format(TASK, task_id, FILES_ATTACHED_TO_TASK, file_ids, file_names_and_ids[0]))
        return file_names_and_ids[0]

    async def perform_changed_schema(  # todo сделать универсальный сервис под разные модели и перенести в base
            self,
            tasks: Task | Sequence[Task],
    ) -> Sequence[dict]:
        """Готовит список словарей для отправки в api."""
        list_changed_response = []
        if not isinstance(tasks, Sequence):
            file_names: Sequence[str] = await self.validate_files_exist_and_get_file_names(tasks.id)
            task_response: dict = await self.change_schema_response(tasks)
            task_response["extra_files"]: list[str] = file_names
            list_changed_response.append(task_response)
        else:
            for task in tasks:
                file_names: Sequence[str] = await self.validate_files_exist_and_get_file_names(task.id)
                task_response: dict = await self.change_schema_response(task)
                task_response["extra_files"]: list[str] = file_names
                list_changed_response.append(task_response)
        return list_changed_response

    async def actualize_object(  # todo перенести в универсальные сервисы? - Лишнее,т.к. у каждой модели свои фишки
            self,
            task_id: int | None,
            in_object: TaskCreate | dict,
            user: User | int
    ) -> Task:
        if not isinstance(in_object, dict):
            in_object = in_object.model_dump()
        if user is None:
            await log.aerror(NO_USER)
            raise HTTPException(status_code=422, detail=NO_USER)
        if isinstance(type(user), int):
            in_object["user_id"] = user
        else:
            in_object["user_id"] = user.id
        task = Task(**in_object)
        if task_id is None:
            return await self._repository.create(task)
        await self.get(task_id)  # check the object to patch exists!
        return await self._repository.update(task_id, task)

    async def get(self, task_id: int) -> Task:
        return await self._repository.get(task_id)

    async def get_all(self) -> Sequence[Task]:
        return await self._repository.get_all()

    async def get_all_opened(self) -> Sequence[Task]:
        return await self._repository.get_all_opened()

    async def get_tasks_ordered(self, user_id: int) -> Sequence[Task]:
        return await self._repository.get_tasks_ordered(user_id)

    async def get_my_tasks_todo(self, user_id: int) -> Sequence[Task]:
        return await self._repository.get_tasks_todo(user_id)

    async def remove(self, task_id: int) -> None: # Sequence[Task]:  # Задача удаляется только вместе с прикрепленными файлами
        # await self._file_repository.remove_all(FileAttached, await self.get_file_ids_from_task(task_id))
        await self._repository.remove(await self._repository.get(task_id))
        # return await self._repository.get_all_id_sorted()

    async def set_files_to_task(self, task_id: int, files_ids: list[int]) -> None:
        """Присваивает задаче список файлов."""
        await self._repository.set_files_to_task(task_id, files_ids)

    async def get_file_ids_from_task(self, task_id: int) -> Sequence[int]:
        """Получить список id файлов, привязанных к задаче, из таблицы TasksFiles m-t-m."""
        task_files_relations: Sequence[TasksFiles] = await self._repository.get_task_files_relations(task_id)
        return [relation.file_id for relation in task_files_relations]

    async def get_file_names_from_task(self, task_id: int) -> Sequence[str]:
        """Получить список файлов, привязанных к задаче."""
        files: Sequence[FileAttached] = await self._repository.get_files_from_task(task_id)
        return [file.name for file in files]

    async def get_file_names_and_ids_from_task(self, task_id: int) -> tuple[list[str], list[int]]:
        """Отдает кортеж из списка имен и id файлов, привязанных к задаче."""
        files: Sequence[FileAttached] = await self._repository.get_files_from_task(task_id)
        return [file.name for file in files], [file.id for file in files]

    async def get_all_file_names_and_ids_from_tasks(self) -> tuple[list[str], list[int]]:
        """Отдает кортеж из списка имен и id файлов, привязанных ко всем задачам."""
        files: Sequence[FileAttached] = await self._repository.get_all_files_from_tasks()
        return [file.name for file in files], [file.id for file in files]
