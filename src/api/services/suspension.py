"""src/api/services/suspension.py"""
from datetime import datetime
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import SuspensionRequest
from src.api.services.base import ContentService
from src.core.db import get_session
from src.core.db.models import Suspension, User
from src.core.db.repository.suspension import SuspensionRepository
from fastapi.encoders import jsonable_encoder

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

    async def get(self, suspension_id: int) -> Suspension:
        return await self._repository.get(suspension_id)

    async def remove(self, suspension_id: int) -> None:
        suspension = await self._repository.get(suspension_id)
        return await self._repository.remove(suspension)


#     async def register(self, site_user_schema: ExternalSiteUserRequest) -> None:
#         site_user = await self._repository.get_or_none(site_user_schema.id)
#         if site_user:
#             await self._repository.update(site_user.id, site_user_schema.to_orm())
#         else:
#             await self._repository.create(site_user_schema.to_orm())



    # async def get_tasks_for_user(self, user_id: int) -> list[Task]:
    #     return await self._repository.get_tasks_for_user(user_id)
    #
    # async def get_user_task_id(self, task_id: int) -> list[Task]:
    #     return await self._repository.get_user_task_id(task_id)
    #
    # async def get_user_tasks_ids(self, ids: list[int]) -> list[Task]:
    #     return await self._repository.get_user_tasks_ids(ids)
