"""src/core/db/repository/file_attached.py"""
from collections.abc import Sequence

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.db.db import get_session
from src.core.db.models import FileAttached, SuspensionsFiles, TasksFiles
from src.core.db.repository.base import ContentRepository


class FileRepository(ContentRepository):
    """Репозиторий для работы с моделью FileAttached."""

    def __init__(self, session: AsyncSession = Depends(get_session)) -> None:
        super().__init__(session, FileAttached)

    async def get_all_for_search_word(
            self,
            search_word: str,
    ) -> Sequence[FileAttached]:
        """Возвращает все объекты модели из базы данных, найденные по поисковому запросу."""
        objects = await self._session.scalars(
            select(self._model)
            .filter(self._model.name.like(f'%{search_word}%'))
            .order_by(self._model.id.desc())
        )
        return objects.all()

    async def get_all_files_from_suspensions(self) -> Sequence[SuspensionsFiles]:  # todo get список файлов за 1 запрос
        """Получить список файлов, прикрепленных ко всем простоям."""
        objects = await self._session.scalars(select(SuspensionsFiles))
        return objects.all()

    async def get_all_files_from_tasks(self) -> Sequence[TasksFiles]:  # todo get list of all attached_files в 1 запрос
        """Получить список файлов, прикрепленных ко всем задачам."""
        objects = await self._session.scalars(select(TasksFiles))
        return objects.all()
