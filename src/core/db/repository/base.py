"""src/core/db/repository/base.py"""
import abc
from datetime import datetime
from typing import TypeVar

from sqlalchemy import false, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import AlreadyExistsException, NotFoundException
from src.core.utils import auto_commit

DatabaseModel = TypeVar("DatabaseModel")


class AbstractRepository(abc.ABC):
    """Абстрактный класс, для реализации паттерна Repository."""

    def __init__(self, session: AsyncSession, model: DatabaseModel) -> None:
        self._session = session
        self._model = model

    async def get_or_none(self, _id: int) -> DatabaseModel | None:
        """Получает из базы объект модели по ID. В случае отсутствия возвращает None."""
        db_obj = await self._session.execute(select(self._model).where(self._model.id == _id))
        return db_obj.scalars().first()

    async def get(self, _id: int) -> DatabaseModel:
        """Получает объект модели по ID. В случае отсутствия объекта бросает ошибку."""
        db_obj = await self.get_or_none(_id)
        if db_obj is None:
            raise NotFoundException(object_name=self._model.__name__, object_id=_id)
        return db_obj

    async def create(self, instance: DatabaseModel) -> DatabaseModel:
        """Создает новый объект модели и сохраняет в базе."""
        self._session.add(instance)
        try:
            await self._session.commit()
        except IntegrityError as exc:
            raise AlreadyExistsException(instance) from exc

        await self._session.refresh(instance)
        return instance

    async def remove(self, instance: DatabaseModel) -> None:
        """Удаляет объект модели из базы данных."""
        await self._session.delete(instance)
        await self._session.commit()

    @auto_commit
    async def update(self, _id: int, instance: DatabaseModel) -> DatabaseModel:
        """Обновляет существующий объект модели в базе."""
        instance.id = _id
        instance = await self._session.merge(instance)
        return instance  # noqa: R504

    @auto_commit
    async def update_all(self, instances: list[dict]) -> list[DatabaseModel]:
        """Обновляет несколько измененных объектов модели в базе."""
        await self._session.execute(update(self._model), instances)
        return instances

    async def get_all(self) -> list[DatabaseModel]:
        """Возвращает все объекты модели из базы данных."""
        objects = await self._session.execute(select(self._model))
        return objects.scalars().all()

    @auto_commit
    async def create_all(self, objects: list[DatabaseModel]) -> None:
        """Создает несколько объектов модели в базе данных."""
        self._session.add_all(objects)

    async def count_all(self) -> int:
        """Возвращает количество юнитов категории."""
        objects = await self._session.execute(select(func.count()).select_from(self._model))
        return objects.scalar()


class ContentRepository(AbstractRepository, abc.ABC):
    @auto_commit
    async def archive_by_ids(self, ids: list[int]) -> None:
        """Изменяет is_archived с False на True у не указанных ids."""
        await self._session.execute(
            update(self._model)
            .where(self._model.is_archived == false())
            .where(self._model.id.not_in(ids))
            .values({"is_archived": True})
        )

    async def get_by_ids(self, ids: list[int]) -> list[int]:
        """Возвращает id объектов модели из базы данных по указанным ids"""
        filtered_ids = await self._session.scalars(select(self._model.id).where(self._model.id.in_(ids)))
        return filtered_ids.all()

    async def get_all_for_period_time(
            self,
            datetime_start: datetime,
            datetime_finish: datetime
    ) -> list[DatabaseModel]:
        """Возвращает все объекты модели из базы данных за указанный период."""
        objects = await self._session.execute(
            select(self._model)
            .where(self._model.datetime_start >= datetime_start)
            .where(self._model.datetime_finish <= datetime_finish)
        )
        return objects.scalars().all()

    async def get_last_id(self) -> int:
        """Возвращает последний по времени объект модели."""
        return await self._session.scalar(
            select(self._model.id)
            .order_by(self._model.id.desc())
        )

    async def sum_time_for_period(self, datetime_start: datetime, datetime_finish: datetime) -> int:
        """Считает время в днях за указанный период."""
        return await self._session.scalar(
            select(func.sum(func.julianday(self._model.datetime_finish) - func.julianday(self._model.datetime_start)))
            .where(self._model.datetime_start >= datetime_start)
            .where(self._model.datetime_finish <= datetime_finish)
        )

    async def count_for_period(self, datetime_start: datetime, datetime_finish: datetime) -> int:
        """Считает количество случаев за указанные период."""
        return await self._session.scalar(
            select(func.count(self._model.datetime_start))
            .where(self._model.datetime_start >= datetime_start)
            .where(self._model.datetime_finish <= datetime_finish)
        )

    async def max_difference_time_for_period(self, datetime_start: datetime, datetime_finish: datetime) -> int:
        """Считает максимальную разницу между началом и концом за указанный период."""
        return await self._session.scalar(
            select(func.max(func.julianday(self._model.datetime_finish) - func.julianday(self._model.datetime_start)))
            .where(self._model.datetime_start >= datetime_start)
            .where(self._model.datetime_finish <= datetime_finish)
        )
