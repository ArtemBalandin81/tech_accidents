"""src/api/services/suspension.py"""
from collections.abc import Sequence
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.constants import *
from src.api.schemas import SuspensionRequest
from src.core.db import get_session
from src.core.db.models import Suspension, User
from src.core.db.repository.suspension import SuspensionRepository
from src.settings import settings


class SuspensionService:
    """Сервис для работы с моделью Suspension."""

    def __init__(
        self,
        suspension_repository: SuspensionRepository = Depends(),
        session: AsyncSession = Depends(get_session)
    ) -> None:
        self._repository: SuspensionRepository = suspension_repository
        self._session: AsyncSession = session

    async def actualize_object(
            self,
            suspension_id: int | None,
            in_object: SuspensionRequest | dict,  # todo сервис не должен принимать pydantic: ждет схему или словарь
            user: User | int
    ):
        if not isinstance(in_object, dict):
            in_object = in_object.dict()  # todo .model_dump()
        if in_object["suspension_start"] >= in_object["suspension_finish"]:
            raise HTTPException(status_code=422, detail=START_FINISH_TIME)
        # todo в доккер идет не корректное сравнение, т.к. сдвигается на - 5 часов время now() - корректируем
        if (
                in_object["suspension_finish"].timestamp()
                > (datetime.now() + timedelta(hours=settings.TIMEZONE_OFFSET)).timestamp()
        ):  # для сравнения дат используем timestamp()
            raise HTTPException(status_code=422, detail=FINISH_NOW_TIME)
        if user is None:
            raise HTTPException(status_code=422, detail="Check USER is not NONE!")
        if type(user) is int:  # Проверяет, что пользователь не передается напрямую id
            in_object["user_id"] = user
        else:
            in_object["user_id"] = user.id
        suspension = Suspension(**in_object)
        if suspension_id is None:  # если suspension_id не передан - создаем, иначе - правим!
            return await self._repository.create(suspension)
        await self.get(suspension_id)  # проверяем, что объект для правки существует!
        return await self._repository.update(suspension_id, suspension)

    async def count_suspensions_for_period(
            self,
            user_id: int,
            suspension_start: datetime = TO_TIME_PERIOD,
            suspension_finish: datetime = FROM_TIME_NOW
    ) -> int:
        if user_id is None:
            return await self._repository.count_for_period(suspension_start, suspension_finish)
        else:
            return await self._repository.count_for_period_for_user(user_id, suspension_start, suspension_finish)

    async def get(self, suspension_id: int) -> Suspension:
        return await self._repository.get(suspension_id)

    async def get_all(self) -> list[any]:
        return await self._repository.get_all()

    async def get_all_for_period_time(
            self,
            suspension_start: datetime = TO_TIME_PERIOD,
            suspension_finish: datetime = FROM_TIME_NOW
    ) -> list[any]:
        return await self._repository.get_all_for_period_time(suspension_start, suspension_finish)

    async def get_last_suspension_id(self, user_id: int) -> int:
        if user_id is None:
            return await self._repository.get_last_id()
        else:
            return await self._repository.get_last_id_for_user(user_id)

    async def get_last_suspension_time(self, user_id: int) -> datetime:
        if user_id is None:
            last_suspension = await self._repository.get(await self._repository.get_last_id())
        else:
            last_suspension = await self._repository.get(await self.get_last_suspension_id(user_id))
        return last_suspension.suspension_start

    async def get_suspensions_for_user(self, user_id: int) -> Sequence[any]:
        return await self._repository.get_suspensions_for_user(user_id)

    async def get_suspensions_for_period_for_user(
        self,
        user_id: int,
        suspension_start: datetime = TO_TIME_PERIOD,
        suspension_finish: datetime = FROM_TIME_NOW
    ) -> Sequence[any]:
        return await self._repository.get_suspensions_for_period_for_user(user_id, suspension_start, suspension_finish)

    async def sum_suspensions_time_for_period(
            self,
            user_id: int,
            suspension_start: datetime = TO_TIME_PERIOD,
            suspension_finish: datetime = FROM_TIME_NOW
    ) -> int:
        if user_id is None:
            total_time_suspensions = await self._repository.sum_time_for_period(suspension_start, suspension_finish)
        else:
            total_time_suspensions = await self._repository.sum_time_for_period_for_user(
                user_id, suspension_start, suspension_finish
            )
        if total_time_suspensions is None:
            return 0
        return round(total_time_suspensions * DISPLAY_TIME)

    async def suspension_max_time_for_period(
            self,
            user_id: int,
            suspension_start: datetime = TO_TIME_PERIOD,
            suspension_finish: datetime = FROM_TIME_NOW
    ) -> int:
        if user_id is None:
            max_time_for_period = await self._repository.suspension_max_time_for_period(
                suspension_start, suspension_finish
            )
        else:
            max_time_for_period = await self._repository.suspension_max_time_for_period_for_user(
                user_id, suspension_start, suspension_finish
            )
        if max_time_for_period is None:
            return 0
        return round(max_time_for_period * DISPLAY_TIME)

    async def remove(self, suspension_id: int) -> None:
        suspension = await self._repository.get(suspension_id)
        return await self._repository.remove(suspension)
