"""src/api/services/suspension.py"""
from fastapi import Depends
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
            in_object: SuspensionRequest | dict,  # Принимает схему или словарь
            user: User
    ) -> None:
        if type(in_object) != dict:
            in_object = in_object.dict()
        if user is not None:
            in_object['user_id'] = user.id
        # print(f'in_objectPrint: {in_object}')  # TODO Отладка, убрать потом
        suspension = Suspension(**in_object)
        await self._repository.create(suspension)

    async def get_all(self) -> list[any]:
        return await self._repository.get_all()
        # suspensions = []  # TODO костыльная реализациия: убрать!
        # for suspension in await self._repository.get_all():
        #     suspensions.append(jsonable_encoder(suspension))
        # return suspensions



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
