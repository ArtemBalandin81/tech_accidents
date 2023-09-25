"""src/api/services/suspension.py"""
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.constants import FROM_TIME_NOW, TO_TIME_PERIOD
from src.api.schemas import SuspensionAnalytics, SuspensionRequest, TotalTimeSuspensions
from src.api.services.base import ContentService
from src.core.db import get_session
from src.core.db.models import Suspension, User
from src.core.db.repository.suspension import SuspensionRepository
from fastapi.encoders import jsonable_encoder

IN_MINS = 60 * 24


class SuspensionService():
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
            in_object: SuspensionRequest | dict,  # Принимает схему или словарь
            user: User
    ):
        if type(in_object) != dict:
            in_object = in_object.dict()
        if in_object["datetime_start"] >= in_object["datetime_finish"]:
            raise HTTPException(status_code=422, detail="start_time >= finish_time")
        if in_object["datetime_finish"] > datetime.now():
            raise HTTPException(status_code=422, detail="Check look ahead finish time")
        if user is not None:
            in_object["user_id"] = user.id
        suspension = Suspension(**in_object)
        if suspension_id is None:  # если suspension_id не передан - создаем, иначе - правим!
            return await self._repository.create(suspension)
        await self._repository.get(suspension_id)  # проверяем, что объект для правки существует!
        return await self._repository.update(suspension_id, suspension)

    async def get_all(self) -> list[any]:
        return await self._repository.get_all()
        # suspensions = []  # TODO костыльная реализациия: убрать!
        # for suspension in await self._repository.get_all():
        #     suspensions.append(jsonable_encoder(suspension))
        # return suspensions

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
        total_time_suspensions = await self._repository.sum_suspensions_time_for_period(datetime_start, datetime_finish)
        if total_time_suspensions is None:
            return 0
        total_time_suspensions_in_mins = round(total_time_suspensions * IN_MINS)
        return total_time_suspensions_in_mins

    async def count_suspensions_for_period(
            self,
            datetime_start: datetime = TO_TIME_PERIOD,
            datetime_finish: datetime = FROM_TIME_NOW
    ) -> int:
        return await self._repository.count_suspensions_for_period(datetime_start, datetime_finish)

    async def max_suspension_time_for_period(
            self,
            datetime_start: datetime = TO_TIME_PERIOD,
            datetime_finish: datetime = FROM_TIME_NOW
    ) -> int:
        max_suspension_time_for_period = round(
            await self._repository.max_suspension_time_for_period(datetime_start, datetime_finish) * IN_MINS
        )
        if max_suspension_time_for_period is None:
            return 0
        return max_suspension_time_for_period


    async def get(self, suspension_id: int) -> Suspension:
        return await self._repository.get(suspension_id)

    async def remove(self, suspension_id: int) -> None:
        suspension = await self._repository.get(suspension_id)
        return await self._repository.remove(suspension)
