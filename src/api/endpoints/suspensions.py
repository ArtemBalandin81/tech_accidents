"""src/api/endpoints/suspensions.py"""
from collections.abc import Sequence
from pathlib import Path
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import PositiveInt

from src.api.constants import *
from src.api.schemas import AnalyticResponse, SuspensionAnalytics, SuspensionRequest, SuspensionResponse
from src.api.schema import (
    AnalyticSuspensionResponse, SuspensionCreateNew, SuspensionResponseNew,
)  # todo "schemas"   # todo rename
from src.api.services import FileService, SuspensionService, UsersService
from src.api.validators import check_start_not_exceeds_finish
from src.core.db.models import Suspension, User
from src.core.db.user import current_superuser, current_user
from src.core.enums import RiskAccidentSource, TechProcess

log = structlog.get_logger()
suspension_router = APIRouter()

SERVICES_DIR = Path(__file__).resolve().parent.parent.parent.parent  # move to settings todo
FILES_DIR = SERVICES_DIR.joinpath(settings.FILES_DOWNLOAD_DIR)  # move to settings todo


async def change_schema_response(suspension: Suspension, user: User) -> AnalyticResponse:  # todo move to services
    """Изменяет и добавляет поля в схему ответа создания, запроса по id и аналитики."""
    suspension_to_dict = suspension.__dict__
    suspension_to_dict["user_email"] = user.email
    suspension_to_dict["business_process"] = TechProcess(str(suspension.tech_process)).name
    return AnalyticResponse(**suspension_to_dict)


@suspension_router.post(
    POST_SUSPENSION_FORM, description=SUSPENSION_CREATE_FORM, summary=SUSPENSION_CREATE_FORM, tags=[SUSPENSIONS_POST]
)
async def create_new_suspension_by_form(
    *,
    file_to_upload: UploadFile = None,
    suspension_start: str = Query(..., example=CREATE_SUSPENSION_FROM_TIME, alias=SUSPENSION_START),
    suspension_finish: str = Query(..., example=CREATE_SUSPENSION_TO_TIME, alias=SUSPENSION_FINISH),
    risk_accident: RiskAccidentSource = Query(..., alias=RISK_ACCIDENT_SOURCE),
    tech_process: TechProcess = Query(..., alias=TECH_PROCESS),
    description: str = Query(..., max_length=256, example=CREATE_DESCRIPTION, alias=SUSPENSION_DESCRIPTION),
    implementing_measures: str = Query(..., max_length=256, example=MEASURES, alias=IMPLEMENTING_MEASURES),
    file_service: FileService = Depends(),
    suspension_service: SuspensionService = Depends(),
    user: User = Depends(current_user),
) -> AnalyticSuspensionResponse:
    """Фиксация случая простоя из формы с возможностью загрузки 1 файла."""
    await check_start_not_exceeds_finish(suspension_start, suspension_finish, DATE_TIME_FORMAT)
    task_object = {
        "suspension_start": datetime.strptime(suspension_start, DATE_TIME_FORMAT),  # reverse in datetime
        "suspension_finish": datetime.strptime(suspension_finish, DATE_TIME_FORMAT),  # reverse in datetime
        "risk_accident": risk_accident.value,
        "tech_process": tech_process.value,
        "description": description,
        "implementing_measures": implementing_measures,
    }
    new_suspension: Suspension = await suspension_service.actualize_object(
        None, SuspensionCreateNew(**task_object), user
    )
    suspension_response: dict = await suspension_service.change_schema_response(new_suspension, user)
    if file_to_upload is None:
        return AnalyticSuspensionResponse(**suspension_response)
    # 2. Download and write files in db and make records in tables "files" & "tasks_files" in db:
    file_timestamp = (datetime.now(TZINFO)).strftime(FILE_DATETIME_FORMAT)  # timestamp in filename
    file_names_and_ids: tuple[list[str], list[PositiveInt]] = await file_service.download_and_write_files_in_db(
        [file_to_upload], FILES_DIR, file_timestamp
    )
    suspension_id = new_suspension.id
    file_id = file_names_and_ids[1]
    file_name = file_names_and_ids[0]
    await suspension_service.set_files_to_suspension(suspension_id, file_id)
    await log.ainfo("{}".format(
        FILES_ATTACHED_TO_SUSPENSION), suspension_id=suspension_id, file_id=file_id, file_name=file_name
    )
    suspension_response["extra_files"]: list[str] = file_name  # add dictionary for AnalyticSuspensionResponse
    return AnalyticSuspensionResponse(**suspension_response)


@suspension_router.post(
    POST_SUSPENSION_FILES_FORM,
    description=SUSPENSION_FILES_CREATE_FORM,
    summary=SUSPENSION_FILES_CREATE_FORM,
    tags=[SUSPENSIONS_POST]
)
async def create_new_suspension_by_form_with_files(
    *,
    files_to_upload: list[UploadFile] = File(...),
    suspension_start: str = Query(..., example=CREATE_SUSPENSION_FROM_TIME, alias=SUSPENSION_START),
    suspension_finish: str = Query(..., example=CREATE_SUSPENSION_TO_TIME, alias=SUSPENSION_FINISH),
    risk_accident: RiskAccidentSource = Query(..., alias=RISK_ACCIDENT_SOURCE),
    tech_process: TechProcess = Query(..., alias=TECH_PROCESS),
    description: str = Query(..., max_length=256, example=CREATE_DESCRIPTION, alias=SUSPENSION_DESCRIPTION),
    implementing_measures: str = Query(..., max_length=256, example=MEASURES, alias=IMPLEMENTING_MEASURES),
    file_service: FileService = Depends(),
    suspension_service: SuspensionService = Depends(),
    user: User = Depends(current_user),
) -> AnalyticSuspensionResponse:
    """Фиксация случая простоя из формы с обязательной загрузкой нескольких файлов."""
    await check_start_not_exceeds_finish(suspension_start, suspension_finish, DATE_TIME_FORMAT)
    task_object = {
        "suspension_start": datetime.strptime(suspension_start, DATE_TIME_FORMAT),  # reverse in datetime
        "suspension_finish": datetime.strptime(suspension_finish, DATE_TIME_FORMAT),  # reverse in datetime
        "risk_accident": risk_accident.value,
        "tech_process": tech_process.value,
        "description": description,
        "implementing_measures": implementing_measures,
    }
    new_suspension: Suspension = await suspension_service.actualize_object(
        None, SuspensionCreateNew(**task_object), user
    )
    suspension_response: dict = await suspension_service.change_schema_response(new_suspension, user)
    # 2. Download and write files in db and make records in tables "files" & "tasks_files" in db:
    file_timestamp = (datetime.now(TZINFO)).strftime(FILE_DATETIME_FORMAT)  # timestamp in filename
    file_names_and_ids: tuple[list[str], list[PositiveInt]] = await file_service.download_and_write_files_in_db(
        files_to_upload, FILES_DIR, file_timestamp
    )
    suspension_id = new_suspension.id
    files_ids = file_names_and_ids[1]
    files_names = file_names_and_ids[0]
    await suspension_service.set_files_to_suspension(suspension_id, files_ids)
    await log.ainfo("{}".format(
        FILES_ATTACHED_TO_SUSPENSION), suspension_id=suspension_id, files_ids=files_ids, files_names=files_names
    )
    suspension_response["extra_files"]: list[str] = files_names  # add dictionary for AnalyticSuspensionResponse
    return AnalyticSuspensionResponse(**suspension_response)


@suspension_router.post(
    ADD_FILES_TO_SUSPENSION,
    description=SET_FILES_LIST_TO_SUSPENSION,
    summary=SET_FILES_LIST_TO_SUSPENSION,
    dependencies=[Depends(current_superuser)],
    tags=[SUSPENSIONS_POST]
)
async def set_files_to_suspension(
    *,
    suspension_id: PositiveInt,
    files_ids: list[PositiveInt] = Query(None, alias=SET_FILES_LIST_TO_SUSPENSION),
    suspension_service: SuspensionService = Depends(),
    file_service: FileService = Depends(),
) -> SuspensionResponseNew:  # todo rename
    """Прикрепление файлов к случаям простоев (запись отношения в БД) (только админ)."""
    await suspension_service.set_files_to_suspension(suspension_id, files_ids)
    files_names: Sequence[str] = await file_service.get_names_by_file_ids(files_ids)
    await log.ainfo(
        "{}{}{}".format(SUSPENSION, suspension_id, FILES_ATTACHED_TO_SUSPENSION),
        suspension_id=suspension_id, files_ids=files_ids, files_names=files_names
    )
    suspension: Suspension = await suspension_service.get(suspension_id)
    return SuspensionResponseNew(**suspension.__dict__, extra_files=files_names)  # todo rename





### OLD ENDPOINTS TO DELETE todo
@suspension_router.post(
    "/form",  # todo в константы
    description="Фиксации случая простоя из формы.",  # todo в константы
    summary="Фиксации случая простоя из формы.",
    tags=["Suspensions POST"]  # todo в константы
)
async def create_new_suspension_by_form(
    *,
    datetime_start: str = Query(..., example=CREATE_SUSPENSION_FROM_TIME, alias=SUSPENSION_START),
    suspension_finish: str = Query(..., example=CREATE_SUSPENSION_TO_TIME, alias=SUSPENSION_FINISH),
    # risk_accident: RiskAccidentSource,
    risk_accident: RiskAccidentSource = Query(..., alias=RISK_ACCIDENT_SOURCE),
    tech_process: TechProcess = Query(..., alias=TECH_PROCESS),
    description: str = Query(..., max_length=256, example=CREATE_DESCRIPTION, alias=SUSPENSION_DESCRIPTION),
    implementing_measures: str = Query(..., max_length=256, example=MEASURES, alias=IMPLEMENTING_MEASURES),
    suspension_service: SuspensionService = Depends(),
    users_service: UsersService = Depends(),
    user: User = Depends(current_user),
) -> AnalyticResponse:
    suspension_start: datetime = datetime.strptime(datetime_start, DATE_TIME_FORMAT)  # обратная конвертация в datetime
    suspension_finish: datetime = datetime.strptime(suspension_finish, DATE_TIME_FORMAT)  # обратная конвертация в datetime
    suspension_object = {
        "suspension_start": suspension_start,
        "suspension_finish": suspension_finish,
        "risk_accident": risk_accident.value,
        "tech_process": tech_process.value,
        "description": description,
        "implementing_measures": implementing_measures,
    }
    suspension = await suspension_service.actualize_object(None, suspension_object, user)
    user = await users_service.get(suspension.user_id)
    return await change_schema_response(suspension, user)


@suspension_router.post(
    MAIN_ROUTE,
    response_model=SuspensionResponse,
    description="Фиксации случая простоя из json.",  # todo в константы
    summary="Фиксации случая простоя из json.",
    tags=["Suspensions POST"]
)
async def create_new_suspension(
    suspension_schemas: SuspensionRequest,
    suspension_service: SuspensionService = Depends(),
    user: User = Depends(current_user),
) -> SuspensionResponse:
    return await suspension_service.actualize_object(None, suspension_schemas, user)


@suspension_router.patch(
    SUSPENSION_ID,
    summary="Редактирование простоя из формы.",
    dependencies=[Depends(current_user)],
    tags=["Suspensions POST"]  # todo в константы
)
async def partially_update_suspension(
    suspension_id: int,
    suspension_schemas: SuspensionRequest,
    suspension_service: SuspensionService = Depends(),
    users_service: UsersService = Depends(),
    user: User = Depends(current_user),
) -> AnalyticResponse:
    suspension = await suspension_service.get(suspension_id)  # проверяем, что объект для правки существует!
    if user.id != suspension.user_id and user.is_superuser is not True:
        raise HTTPException(status_code=403, detail=ONLY_AUTHOR)
    await suspension_service.actualize_object(suspension_id, suspension_schemas, user)
    suspension = await suspension_service.get(suspension_id)
    user = await users_service.get(suspension.user_id)
    return await change_schema_response(suspension, user)


@suspension_router.get(
    MAIN_ROUTE,
    response_model_exclude_none=True,
    description="Список всех случаев простоя.",  # todo в константы
    summary="Список всех случаев простоя.",
    tags=["Suspensions GET"]  # todo в константы
)
async def get_all_suspensions(suspension_service: SuspensionService = Depends()) -> list[SuspensionResponse]:
    return await suspension_service.get_all()


@suspension_router.get(
    ANALYTICS,
    response_model_exclude_none=True,
    description="Список случаев простоя за период.",  # todo в константы
    summary="Список случаев простоя за период.",
    tags=["Suspensions ANALYTICS"]  # todo в константы
)
async def get_all_for_period_time(
    suspension_start: str = Query(..., example=ANALYTIC_FROM_TIME, alias=SUSPENSION_START),  # для отображения в сваггер
    suspension_finish: str = Query(..., example=ANALYTIC_TO_TIME, alias=SUSPENSION_FINISH),  # для отображения в сваггер
    user_id: Optional[int] = Query(None, example="", alias=USER_ID),
    suspension_service: SuspensionService = Depends(),
    users_service: UsersService = Depends(),
) -> SuspensionAnalytics:
    suspension_start: datetime = datetime.strptime(suspension_start, DATE_TIME_FORMAT)  # обратная конвертация в datetime
    suspension_finish: datetime = datetime.strptime(suspension_finish, DATE_TIME_FORMAT)  # обратная конвертация в datetime
    if user_id is None:
        suspensions = await suspension_service.get_all_for_period_time(suspension_start, suspension_finish)
    else:
        suspensions = await suspension_service.get_suspensions_for_period_for_user(
            user_id, suspension_start, suspension_finish
        )
    suspensions_list = []
    for suspension in suspensions:  # todo это работа сервиса, перенести
        user = await users_service.get(suspension.user_id)  # todo избавиться от дергания базы: загружать за 1 раз
        suspension_to_dict = await change_schema_response(suspension, user)
        suspensions_list.append(suspension_to_dict)
    return SuspensionAnalytics(  # todo аналитику тоже придется перенастроить на использование юзера, или нет
        suspensions_in_mins_total=(
            await suspension_service.sum_suspensions_time_for_period(user_id, suspension_start, suspension_finish)
        ),
        suspensions_total=(
            await suspension_service.count_suspensions_for_period(user_id, suspension_start, suspension_finish)
        ),
        suspension_max_time_for_period=(
            await suspension_service.suspension_max_time_for_period(user_id, suspension_start, suspension_finish)
        ),
        last_time_suspension=await suspension_service.get_last_suspension_time(user_id),
        last_time_suspension_id=await suspension_service.get_last_suspension_id(user_id),
        # suspensions=suspensions,
        suspensions_detailed=suspensions_list
    )


@suspension_router.get(
    MY_SUSPENSIONS,
    response_model_exclude_none=True,
    description="Список случаев простоя текущего пользователя.",  # todo в константы
    summary="Список случаев простоя текущего пользователя.",
    tags=["Suspensions GET"]  # todo в константы
)
async def get_my_suspensions(
    suspension_service: SuspensionService = Depends(),
    user: User = Depends(current_user)
) -> Sequence[SuspensionResponse]:
    return await suspension_service.get_suspensions_for_user(user.id)


@suspension_router.get(
    SUSPENSION_ID,
    description="Информация о случае простоя по его id.",  # todo в константы
    summary="Информация о случае простоя по его id.",
    tags=["Suspensions GET"]  # todo в константы
)
async def get_suspension_by_id(
        suspension_id: int,
        suspension_service: SuspensionService = Depends(),
        users_service: UsersService = Depends(),
) -> AnalyticResponse:
    suspension = await suspension_service.get(suspension_id)
    user = await users_service.get(suspension.user_id)
    return await change_schema_response(suspension, user)


@suspension_router.delete(
    SUSPENSION_ID,
    dependencies=[Depends(current_superuser)],
    summary="Удалить простой (только админ).",
    tags=["Suspensions POST"]
)
async def remove_suspension(suspension_id: int, suspension_service: SuspensionService = Depends()) -> None:
    return await suspension_service.remove(suspension_id)
