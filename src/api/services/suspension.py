"""src/api/services/suspension.py"""

from collections.abc import Sequence

import structlog
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.constants import *
from src.api.schema import SuspensionCreate
from src.core.db import get_session
from src.core.db.models import FileAttached, Suspension, SuspensionsFiles, User
from src.core.db.repository import (FileRepository, SuspensionRepository,
                                    UsersRepository)
from src.core.enums import TechProcess

log = structlog.get_logger()


class SuspensionService:
    """Сервис для работы с моделью Suspension."""

    def __init__(
        self,
        file_repository: FileRepository = Depends(),
        suspension_repository: SuspensionRepository = Depends(),
        users_repository: UsersRepository = Depends(),
        session: AsyncSession = Depends(get_session)
    ) -> None:
        self._file_repository: FileRepository = file_repository
        self._repository: SuspensionRepository = suspension_repository
        self._users_repository: UsersRepository = users_repository
        self._session: AsyncSession = session

    async def change_schema_response(self, suspension: Suspension, user: User = None) -> dict:
        """Изменяет и добавляет поля в словарь в целях наглядного представления в ответе api."""
        if user is None:
            user: User = await self._users_repository.get(suspension.user_id)  # todo очень затратно!
            await log.adebug("{}".format(USER_NOT_PROVIDED), user=user)
        suspension_to_dict = suspension.__dict__
        suspension_to_dict["user_email"] = user.email
        suspension_to_dict["business_process"] = TechProcess(str(suspension.tech_process)).name
        suspension_to_dict["extra_files"] = []
        return suspension_to_dict

    async def validate_files_exist_and_get_file_names(  # move to services/base.py todo
            self,
            suspension_id: int,
    ) -> Sequence[str] | None:
        """Отдает имена файлов из таблицы SuspensionsFiles, если они записаны в БД и запись (m-t-m) им соответствует."""
        files_ids_from_suspension_files_relations: Sequence[int] = (
            await self.get_file_ids_from_suspension(suspension_id)  # todo
        )
        files_names_and_ids_from_file_attached: tuple[list[str], list[int]] = (
            await self.get_file_names_and_ids_from_suspension(suspension_id)  # todo
        )
        if len(files_ids_from_suspension_files_relations) != len(files_names_and_ids_from_file_attached[0]):
            details = "{}{}{}{}{}".format(  # todo возможно, это избыточная проверка!
                SUSPENSION, suspension_id, SUSPENSION_FILES_MISMATCH, files_ids_from_suspension_files_relations,
                files_names_and_ids_from_file_attached[0]
            )
            await log.aerror(
                details,
                suspension_id=suspension_id,
                ids_from_suspension_files=files_ids_from_suspension_files_relations,
                ids_from_file_attached=files_names_and_ids_from_file_attached[1]
            )
            raise HTTPException(status_code=206, detail=details)
        return files_names_and_ids_from_file_attached[0]

    async def perform_changed_schema(  # move to services/base.py (change_schema_response - своя, а сервис общий) todo
            self,
            suspensions: Suspension | Sequence[Suspension],
            user: User | None = None
    ) -> Sequence[dict]:
        """Готовит список словарей для отправки в api."""
        list_changed_response = []
        if not isinstance(suspensions, Sequence):
            file_names: Sequence[str] = await self.validate_files_exist_and_get_file_names(suspensions.id)
            suspensions_response: dict = await self.change_schema_response(suspensions, user)
            suspensions_response["extra_files"]: list[str] = file_names
            list_changed_response.append(suspensions_response)
        else:
            for suspension in suspensions:
                file_names: Sequence[str] = await self.validate_files_exist_and_get_file_names(suspension.id)
                suspension_response: dict = await self.change_schema_response(suspension, user)
                suspension_response["extra_files"]: list[str] = file_names
                list_changed_response.append(suspension_response)
        return list_changed_response

    async def actualize_object(  # move to services/base.py todo
            self,
            suspension_id: int | None,
            in_object: SuspensionCreate | dict,
            user: User | int
    ) -> Suspension:
        """Создает или изменяет объект модели в базе."""
        if not isinstance(in_object, dict):
            in_object = in_object.model_dump()
        if user is None:
            await log.aerror(NO_USER, user=user)
            raise HTTPException(status_code=422, detail=NO_USER)
        if isinstance(type(user), int):
            in_object["user_id"] = user
        else:
            in_object["user_id"] = user.id
        suspension = Suspension(**in_object)
        if suspension_id is None:
            return await self._repository.create(suspension)
        return await self._repository.update(suspension_id, suspension)

    async def get(self, suspension_id: int) -> Suspension:  # move to services/base.py todo
        """Возвращает объект модели из базы."""
        return await self._repository.get(suspension_id)

    async def get_all(self) -> Sequence[Suspension]:  # move to services/base.py todo
        """Возвращает все объекты модели из базы."""
        return await self._repository.get_all()  # todo сделать новую с user, чтобы не делать 1000 запросов к БД

    async def count_suspensions_for_period(
            self,
            user_id: int,
            suspension_start: datetime = TO_TIME_PERIOD,
            suspension_finish: datetime = FROM_TIME_NOW
    ) -> int:
        """Количество простоев в периоде для пользователя (или для всех, если пользователь не передан)."""
        return await self._repository.count_for_period_for_user(user_id, suspension_start, suspension_finish)

    async def get_last_suspension_id(self, user_id: int) -> int:
        """Возвращает id крайнего случая простоя, зафиксированного текущим пользователем (или всех)."""
        if user_id is None:
            return await self._repository.get_last_id()
        else:
            return await self._repository.get_last_id_for_user(user_id)

    async def get_last_suspension_time(self, user_id: int) -> datetime:
        """Возвращает время крайнего случая простоя, зафиксированного текущим пользователем (или всеми)."""
        if user_id is None:
            last_suspension = await self._repository.get(await self._repository.get_last_id())
        else:
            last_suspension = await self._repository.get(await self.get_last_suspension_id(user_id))
        return last_suspension.suspension_start

    async def get_all_my_suspensions(self, user_id: int) -> Sequence[Suspension]:
        """Возвращает из БД все случаи простоя, зафиксированные текущим пользователем."""
        return await self._repository.get_suspensions_for_user(user_id)

    async def get_suspensions_for_users(
        self,
        user_id: int | None,
        suspension_start: datetime = TO_TIME_PERIOD,
        suspension_finish: datetime = FROM_TIME_NOW
    ) -> Sequence[Suspension]:
        """Cписок простоев в периоде для пользователя (или для всех, если пользователь не передан)."""
        return await self._repository.get_suspensions_for_period_for_user(user_id, suspension_start, suspension_finish)

    async def sum_suspensions_time_for_period(
            self,
            user_id: int | None,
            suspension_start: datetime = TO_TIME_PERIOD,
            suspension_finish: datetime = FROM_TIME_NOW
    ) -> int:
        """Сумма простоев в периоде для пользователя (или для всех, если пользователь не передан)."""
        total_time_suspensions = await self._repository.sum_time_for_period_for_user(
            user_id, suspension_start, suspension_finish
        )
        if total_time_suspensions is None:
            return 0
        return round(total_time_suspensions * settings.SUSPENSION_DISPLAY_TIME)  # in mins as part of a day

    async def suspension_max_time_for_period(
            self,
            user_id: int | None,
            suspension_start: datetime = TO_TIME_PERIOD,
            suspension_finish: datetime = FROM_TIME_NOW
    ) -> int:
        """Максимальный простой в периоде для пользователя (или для всех, если пользователь не передан)."""
        max_time_for_period = await self._repository.suspension_max_time_for_period_for_user(
            user_id, suspension_start, suspension_finish
        )
        if max_time_for_period is None:
            return 0
        return round(max_time_for_period * settings.SUSPENSION_DISPLAY_TIME)  # in mins as part of a day

    async def remove(self, suspension_id: int) -> None:
        """Удаляет объект модели из базы данных."""
        return await self._repository.remove(await self._repository.get(suspension_id))

    async def set_files_to_suspension(self, suspension_id: int, files_ids: list[int]) -> None:
        """Присваивает простою список файлов."""  # move to services/base.py todo
        await self._repository.set_files_to_suspension(suspension_id, files_ids)

    async def get_file_ids_from_suspension(self, suspension_id: int) -> Sequence[int]:  # move to services/base.py todo
        """Получить список ids файлов, привязанных к простою, из таблицы SuspensionsFiles m-t-m."""
        suspension_files_relations: Sequence[SuspensionsFiles] = (
            await self._repository.get_suspension_files_relations(suspension_id)
        )
        return [relation.file_id for relation in suspension_files_relations]

    async def get_file_names_and_ids_from_suspension(self, suspension_id: int) -> tuple[list[str], list[int]]:
        """Отдает кортеж из списка имен и ids файлов, привязанных к простою из таблицы FileAttached."""  # todo
        files: Sequence[FileAttached] = await self._repository.get_files_from_suspension(suspension_id)
        return [file.name for file in files], [file.id for file in files]

    async def get_all_file_names_and_ids_from_suspensions(self) -> tuple[list[str], list[int]]:
        """Отдает кортеж из списка имен и ids файлов, привязанных ко всем задачам."""  # move to services/base.py todo
        files: Sequence[FileAttached] = await self._repository.get_all_files_from_suspensions()
        return [file.name for file in files], [file.id for file in files]
