"""src/core/db/repository/suspension.py"""
from collections.abc import Sequence
from datetime import datetime

from fastapi import Depends
from sqlalchemy import delete, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.db.db import get_session
from src.core.db.models import FileAttached, Suspension, SuspensionsFiles
from src.core.db.repository.base import ContentRepository
from src.core.exceptions import NotFoundException


class SuspensionRepository(ContentRepository):
    """Репозиторий для работы с моделью Suspension."""

    def __init__(self, session: AsyncSession = Depends(get_session)) -> None:
        super().__init__(session, Suspension)

    async def count_for_period_for_user(
            self,
            user_id: int,
            suspension_start: datetime,
            suspension_finish: datetime,

    ) -> int:
        """Считает количество простоев за указанные период для пользователя."""
        return await self._session.scalar(
            select(func.count(Suspension.suspension_start))
            .where(Suspension.user_id == user_id)
            .where(Suspension.suspension_start >= suspension_start)
            .where(Suspension.suspension_finish <= suspension_finish)
        )

    async def get_all(self) -> Sequence[Suspension]:
        """Возвращает все объекты модели из базы данных, отсортированные по времени."""
        objects = await self._session.scalars(
            select(Suspension)
            .order_by(Suspension.suspension_start.desc())
        )
        return objects.all()

    async def get_last_id_for_user(self, user_id: int) -> int:
        """Возвращает последний по времени простой для пользователя."""
        return await self._session.scalar(
            select(Suspension.id)
            .where(Suspension.user_id == user_id)
            .order_by(Suspension.id.desc())
        )

    async def get_suspensions_for_user(self, user_id: int, limit: int = 3, offset: int = 0) -> Sequence[Suspension]:
        """Получить список простоев пользователя."""
        suspensions_for_user = await self._session.scalars(
            select(Suspension)
            .where(Suspension.user_id == user_id)
            # .limit(limit)  # todo реализовать пагинацию
            # .offset(offset)
            .order_by(Suspension.suspension_start.desc())
        )
        return suspensions_for_user.all()

    async def get_suspensions_for_period_for_user(
            self,
            user_id: int,
            suspension_start: datetime,
            suspension_finish: datetime
    ) -> Sequence[Suspension]:
        """Получить список простоев пользователя за выбранный период времени."""
        suspensions_for_user_for_period = await self._session.scalars(
            select(Suspension)
            .where(Suspension.user_id == user_id)
            .where(Suspension.suspension_start >= suspension_start)
            .where(Suspension.suspension_finish <= suspension_finish)
            .order_by(Suspension.suspension_start.desc())
            .order_by(Suspension.suspension_start.desc())
        )
        return suspensions_for_user_for_period.all()

    async def suspension_max_time_for_period_for_user(
            self,
            user_id: int,
            suspension_start: datetime,
            suspension_finish: datetime
    ) -> int:
        """Считает максимальную разницу между началом и концом за указанный период для пользователя."""
        return await self._session.scalar(
            select(func.max(func.julianday(
                Suspension.suspension_finish) - func.julianday(Suspension.suspension_start))
                   )
            .where(Suspension.user_id == user_id)
            .where(Suspension.suspension_start >= suspension_start)
            .where(Suspension.suspension_finish <= suspension_finish)
        )

    async def sum_time_for_period_for_user(
            self,
            user_id: int,
            suspension_start: datetime,
            suspension_finish: datetime,

    ) -> int:
        """Считает время в днях за указанный период для пользователя."""
        return await self._session.scalar(
            select(func.sum(func.julianday(
                Suspension.suspension_finish) - func.julianday(Suspension.suspension_start))
                   )
            .where(Suspension.user_id == user_id)
            .where(Suspension.suspension_start >= suspension_start)
            .where(Suspension.suspension_finish <= suspension_finish)
        )

    async def set_files_to_suspension(self, suspension_id: int, files_ids: list[int]) -> None:
        """Присваивает простою список файлов."""  # in to repository/base.py todo
        await self._session.commit()
        async with self._session.begin():
            suspension = await self._session.scalar(select(Suspension).where(Suspension.id == suspension_id))
            if suspension is None:
                raise NotFoundException(object_name=Suspension.__name__, object_id=suspension_id)
            await self._session.execute(delete(SuspensionsFiles).where(SuspensionsFiles.suspension_id == suspension_id))
            if files_ids:
                await self._session.execute(
                    insert(SuspensionsFiles).values(
                        [{"suspension_id": suspension_id, "file_id": file_id} for file_id in files_ids]
                    )
                )

    async def get_suspension_files_relations(self, suspension_id: int) -> Sequence[SuspensionsFiles]:
        """Получить список отношений простой-файл."""  # in to repository/base.py todo
        suspension_files_relations = await self._session.scalars(
            select(SuspensionsFiles)
            .where(SuspensionsFiles.suspension_id == suspension_id)
            .order_by(SuspensionsFiles.file_id.asc())
        )
        return suspension_files_relations.all()

    async def get_files_from_suspension(self, suspension_id: int) -> Sequence[FileAttached]:
        """Получить список файлов, прикрепленных к простою."""
        files = await self._session.scalars(
            select(FileAttached)
            .join(Suspension.files)
            .where(Suspension.id == suspension_id)
        )
        return files.all()

    async def get_all_files_from_suspensions(self) -> Sequence[FileAttached]:  # TODO need refactoring
        """Получить список файлов, прикрепленных ко всем простоям."""  # RENAME/DELETE and use get_all instead todo
        files = await self._session.scalars(select(FileAttached))
        return files.all()
