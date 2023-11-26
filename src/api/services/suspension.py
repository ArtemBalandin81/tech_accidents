"""src/api/services/suspension.py"""
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.constants import DISPLAY_TIME, FROM_TIME_NOW, TO_TIME_PERIOD, TZINFO
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
        if type(in_object) != dict:
            in_object = in_object.dict()
        if in_object["datetime_start"] >= in_object["datetime_finish"]:
            raise HTTPException(status_code=422, detail="Check start_time >= finish_time")
        # todo в доккер идет не корректное сравнение, т.к. сдвигается на - 5 часов время now() - корректируем
        if (
                in_object["datetime_finish"].timestamp()
                > (datetime.now() + timedelta(hours=settings.TIMEZONE_OFFSET)).timestamp()
        ):  # для сравнения дат используем timestamp()
            raise HTTPException(status_code=422, detail="Check finish_time > current time")
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

    async def get_all(self) -> list[any]:
        return await self._repository.get_all()

    async def get_all_for_period_time(
            self,
            datetime_start: datetime = TO_TIME_PERIOD,
            datetime_finish: datetime = FROM_TIME_NOW
    ) -> list[any]:
        return await self._repository.get_all_for_period_time(datetime_start, datetime_finish)

    async def sum_suspensions_time_for_period(
            self,
            datetime_start: datetime = TO_TIME_PERIOD,
            datetime_finish: datetime = FROM_TIME_NOW
    ) -> int:
        total_time_suspensions = await self._repository.sum_time_for_period(datetime_start, datetime_finish)
        if total_time_suspensions is None:
            return 0
        return round(total_time_suspensions * DISPLAY_TIME)

    async def count_suspensions_for_period(
            self,
            datetime_start: datetime = TO_TIME_PERIOD,
            datetime_finish: datetime = FROM_TIME_NOW
    ) -> int:
        return await self._repository.count_for_period(datetime_start, datetime_finish)

    async def max_suspension_time_for_period(
            self,
            datetime_start: datetime = TO_TIME_PERIOD,
            datetime_finish: datetime = FROM_TIME_NOW
    ) -> int:
        max_suspension_time_for_period = (
            await self._repository.max_difference_time_for_period(datetime_start, datetime_finish)
        )
        if max_suspension_time_for_period is None:
            return 0
        return round(max_suspension_time_for_period * DISPLAY_TIME)

    async def get(self, suspension_id: int) -> Suspension:
        return await self._repository.get(suspension_id)

    async def get_last_suspension_id(self) -> int:
        return await self._repository.get_last_id()

    async def get_last_suspension_time(self) -> datetime:
        last_suspension = await self._repository.get(await self._repository.get_last_id())
        return last_suspension.datetime_start

    async def remove(self, suspension_id: int) -> None:
        suspension = await self._repository.get(suspension_id)
        return await self._repository.remove(suspension)
