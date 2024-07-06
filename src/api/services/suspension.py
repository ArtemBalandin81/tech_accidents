"""src/api/services/suspension.py"""
from collections.abc import Sequence
from datetime import datetime, timedelta

import structlog
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.constants import *
from src.api.schemas import SuspensionRequest
from src.api.schema import (AnalyticSuspensionResponse, SuspensionCreateNew, SuspensionResponseNew,)
from src.core.db import get_session
from src.core.db.models import FileAttached, Suspension, SuspensionsFiles, User
from src.core.db.repository import FileRepository, SuspensionRepository, UsersRepository
from src.core.enums import TechProcess
# from src.core.db.repository.file_attached import FileRepository
# from src.core.db.repository.suspension import SuspensionRepository
from src.settings import settings

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
            user = await self._users_repository.get(suspension.user_id)
            await log.ainfo("{}".format(USER_NOT_PROVIDED), user=user)
        suspension_to_dict = suspension.__dict__
        suspension_to_dict["user_email"] = user.email
        suspension_to_dict["business_process"] = TechProcess(str(suspension.tech_process)).name
        suspension_to_dict["extra_files"] = []
        return suspension_to_dict

    async def validate_files_exist_and_get_file_names(  # todo сделать универсальный сервис
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

    async def perform_changed_schema(  # todo сделать универсальный сервис под разные модели и перенести в base
            self,
            suspensions: Suspension | Sequence[Suspension],
    ) -> Sequence[dict]:
        """Готовит список словарей для отправки в api."""
        list_changed_response = []
        if not isinstance(suspensions, Sequence):
            file_names: Sequence[str] = await self.validate_files_exist_and_get_file_names(suspensions.id)
            suspensions_response: dict = await self.change_schema_response(suspensions)
            suspensions_response["extra_files"]: list[str] = file_names
            list_changed_response.append(suspensions_response)
        else:
            for suspension in suspensions:
                file_names: Sequence[str] = await self.validate_files_exist_and_get_file_names(suspension.id)
                suspension_response: dict = await self.change_schema_response(suspension)
                suspension_response["extra_files"]: list[str] = file_names
                list_changed_response.append(suspension_response)
        return list_changed_response

    # async def actualize_object(
    #         self,
    #         suspension_id: int | None,
    #         in_object: SuspensionRequest | dict,  # todo сервис не должен принимать pydantic: ждет схему или словарь
    #         user: User | int
    # ):
    #     """Создает или изменяет объект модели в базе."""
    #     if not isinstance(in_object, dict):
    #         in_object = in_object.dict()  # todo .model_dump()
    #     if in_object["suspension_start"] >= in_object["suspension_finish"]:
    #         raise HTTPException(status_code=422, detail=START_FINISH_TIME)
    #     # todo в доккер идет не корректное сравнение, т.к. сдвигается на - 5 часов время now() - корректируем
    #     if (
    #             in_object["suspension_finish"].timestamp()
    #             > (datetime.now() + timedelta(hours=settings.TIMEZONE_OFFSET)).timestamp()
    #     ):  # для сравнения дат используем timestamp()
    #         raise HTTPException(status_code=422, detail=FINISH_NOW_TIME)
    #     if user is None:
    #         raise HTTPException(status_code=422, detail="Check USER is not NONE!")
    #     if type(user) is int:  # Проверяет, что пользователь не передается напрямую id
    #         in_object["user_id"] = user
    #     else:
    #         in_object["user_id"] = user.id
    #     suspension = Suspension(**in_object)
    #     if suspension_id is None:  # если suspension_id не передан - создаем, иначе - правим!
    #         return await self._repository.create(suspension)
    #     await self.get(suspension_id)  # проверяем, что объект для правки существует!
    #     return await self._repository.update(suspension_id, suspension)

    async def actualize_object(  # move to services/base.py todo
            self,
            suspension_id: int | None,
            in_object: SuspensionCreateNew | dict,
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

    async def get(self, suspension_id: int) -> Suspension:
        """Возвращает объект модели из базы."""
        return await self._repository.get(suspension_id)

    async def get_all(self) -> Sequence[Suspension]:
        """Возвращает все объекты модели из базы."""
        return await self._repository.get_all()






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



    # async def get_all(self) -> list[any]:  # todo delete
    #     return await self._repository.get_all()

    async def get_all_for_period_time(  # todo needed refactoring and docstrings
            self,
            suspension_start: datetime = TO_TIME_PERIOD,
            suspension_finish: datetime = FROM_TIME_NOW
    ) -> list[any]:
        return await self._repository.get_all_for_period_time(suspension_start, suspension_finish)

    async def get_last_suspension_id(self, user_id: int) -> int:  # todo needed refactoring and docstrings
        if user_id is None:
            return await self._repository.get_last_id()
        else:
            return await self._repository.get_last_id_for_user(user_id)

    async def get_last_suspension_time(self, user_id: int) -> datetime:  # todo needed refactoring and docstrings
        if user_id is None:
            last_suspension = await self._repository.get(await self._repository.get_last_id())
        else:
            last_suspension = await self._repository.get(await self.get_last_suspension_id(user_id))
        return last_suspension.suspension_start

    async def get_suspensions_for_user(self, user_id: int) -> Sequence[any]:  # todo needed refactoring and docstrings
        return await self._repository.get_suspensions_for_user(user_id)

    async def get_suspensions_for_period_for_user(  # todo needed refactoring and docstrings
        self,
        user_id: int,
        suspension_start: datetime = TO_TIME_PERIOD,
        suspension_finish: datetime = FROM_TIME_NOW
    ) -> Sequence[any]:
        return await self._repository.get_suspensions_for_period_for_user(user_id, suspension_start, suspension_finish)

    async def sum_suspensions_time_for_period(  # todo needed refactoring and docstrings
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

    async def suspension_max_time_for_period(  # todo needed refactoring and docstrings
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

    async def remove(self, suspension_id: int) -> None:  # todo needed refactoring and docstrings
        suspension = await self._repository.get(suspension_id)
        return await self._repository.remove(suspension)

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
