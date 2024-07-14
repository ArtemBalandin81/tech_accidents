"""src/core/db/repository/base.py"""

import abc
from typing import Sequence, TypeVar

from sqlalchemy import delete, func, select, update
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
        return await self._session.scalar(select(self._model).where(self._model.id == _id))

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
    async def remove_all(self, instance: DatabaseModel, instances: Sequence[int]) -> None:
        """Удаляет объекты модели из базы данных."""
        await self._session.execute(delete(instance).where(instance.id.in_(instances)))

    @auto_commit
    async def update(self, _id: int, instance: DatabaseModel) -> DatabaseModel:
        """Обновляет существующий объект модели в базе."""
        instance.id = _id
        instance = await self._session.merge(instance)
        await self._session.commit()
        await self._session.refresh(instance)
        return instance  # noqa: R504

    @auto_commit
    async def update_all(self, instances: list[dict]) -> list[DatabaseModel]:
        """Обновляет несколько измененных объектов модели в базе."""
        await self._session.execute(update(self._model), instances)
        return instances

    async def get_all(self) -> Sequence[DatabaseModel]:
        """Возвращает все объекты модели из базы данных."""
        objects = await self._session.scalars(select(self._model))
        return objects.all()

    async def get_by_ids(self, instances: Sequence[int]) -> Sequence[DatabaseModel]:
        """Возвращает объекты модели из базы данных по списку ids."""
        objects = await self._session.scalars(select(self._model).where(self._model.id.in_(instances)))
        return objects.all()

    @auto_commit
    async def create_all(self, objects: Sequence[DatabaseModel]) -> Sequence[DatabaseModel]:
        """Создает и возвращает несколько объектов модели в базе данных."""
        self._session.add_all(objects)
        return objects

    async def count_all(self) -> int:
        """Возвращает количество юнитов категории."""
        return await self._session.scalar(select(func.count()).select_from(self._model))


class ContentRepository(AbstractRepository, abc.ABC):
    """Класс контента, для дополнения паттерна Repository."""

    async def get_last_id(self) -> int:
        """Возвращает крайний объект модели."""
        return await self._session.scalar(select(self._model.id).order_by(self._model.id.desc()))
