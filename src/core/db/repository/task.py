"""src/core/db/repository/task.py"""
from collections.abc import Sequence

from fastapi import Depends
from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.db.db import get_session
from src.core.db.models import FileAttached, Task, TasksFiles
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

    async def get_all_id_ordered(self) -> Sequence[Task]:
        """Возвращает все задачи из базы данных, отсортированные по id."""
        objects = await self._session.scalars(
            select(Task)
            .order_by(Task.id.desc())
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

    async def set_files_to_task(self, task_id: int, files_ids: list[int]) -> None:
        """Присваивает задаче список файлов."""
        await self._session.commit()
        async with self._session.begin():
            await self._session.execute(delete(TasksFiles).where(TasksFiles.task_id == task_id))
            if files_ids:
                await self._session.execute(
                    insert(TasksFiles).values(
                        [{"task_id": task_id, "file_id": file_id} for file_id in files_ids]
                    )
                )

    async def get_task_files_relations(self, task_id: int) -> Sequence[TasksFiles]:  # todo это не файлы а связи!!!
        """Получить список отношений задача-файл."""
        task_files_relations = await self._session.scalars(
            select(TasksFiles)
            .where(TasksFiles.task_id == task_id)
            .order_by(TasksFiles.file_id.asc())
        )
        return task_files_relations.all()


    async def get_files_from_task(self, task_id: int) -> Sequence[FileAttached]:
        """Получить список файлов, прикрепленных к задаче."""
        files = await self._session.scalars(
            select(FileAttached)
            .join(Task.files)
            .where(Task.id == task_id))
        return files.all()
