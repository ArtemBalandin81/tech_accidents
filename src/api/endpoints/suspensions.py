"""src/api/endpoints/suspensions.py"""
from collections.abc import Sequence
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.constants import *
from src.api.schemas import (
    AnalyticResponse, SuspensionAnalytics, SuspensionRequest, SuspensionResponse
)
from src.api.services import SuspensionService, UsersService
from src.core.db.models import Suspension, User
from src.core.db.user import current_superuser, current_user, unauthorized_user

from src.core.enums import RiskAccidentSource, TechProcess

suspension_router = APIRouter()


async def change_schema_response(suspension: Suspension, user: User) -> AnalyticResponse:
    """Изменяет и добавляет поля в схему ответа создания, запроса по id и аналитики."""
    suspension_to_dict = suspension.__dict__  # todo криво, поменяй метод, метод дублируется
    suspension_to_dict["user_email"] = user.email
    suspension_to_dict["business_process"] = TechProcess(suspension.tech_process).name
    return AnalyticResponse(**suspension_to_dict)


@suspension_router.post(
    "/form",  # todo в константы
    description="Фиксации случая простоя из формы.",  # todo в константы
    summary="Фиксации случая простоя из формы.",
    tags=["Suspensions POST"]  # todo в константы
)
async def create_new_suspension_by_form(
    *,
    datetime_start: str = Query(..., example=CREATE_SUSPENSION_FROM_TIME, alias=SUSPENSION_START),
    datetime_finish: str = Query(..., example=CREATE_SUSPENSION_TO_TIME, alias=SUSPENSION_FINISH),
    # risk_accident: RiskAccidentSource,
    risk_accident: RiskAccidentSource = Query(..., alias=RISK_ACCIDENT_SOURCE),
    tech_process: TechProcess = Query(..., alias=TECH_PROCESS),
    description: str = Query(..., max_length=256, example=CREATE_DESCRIPTION, alias=SUSPENSION_DESCRIPTION),
    implementing_measures: str = Query(..., max_length=256, example=MEASURES, alias=IMPLEMENTING_MEASURES),
    suspension_service: SuspensionService = Depends(),
    users_service: UsersService = Depends(),
    user: User = Depends(current_user),
) -> AnalyticResponse:
    datetime_start: datetime = datetime.strptime(datetime_start, DATE_TIME_FORMAT)  # обратная конвертация в datetime
    datetime_finish: datetime = datetime.strptime(datetime_finish, DATE_TIME_FORMAT)  # обратная конвертация в datetime
    suspension_object = {
        "datetime_start": datetime_start,
        "datetime_finish": datetime_finish,
        "risk_accident": risk_accident,
        "tech_process": tech_process,
        "description": description,
        "implementing_measures": implementing_measures,
    }
    suspension = await suspension_service.actualize_object(None, suspension_object, user)
    user = await users_service.get(suspension.user_id)
    return await change_schema_response(suspension, user)


@suspension_router.post(
    GET_ALL_ROUTE,
    response_model=SuspensionResponse,
    description="Фиксации случая простоя из json.",  # todo в константы
    summary="Фиксации случая простоя из json.",
    tags=["Suspensions POST"]  # todo в константы
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
    GET_ALL_ROUTE,
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
    datetime_start: str = Query(..., example=ANALYTIC_FROM_TIME, alias=SUSPENSION_START),  # для отображения в сваггер
    datetime_finish: str = Query(..., example=ANALYTIC_TO_TIME, alias=SUSPENSION_FINISH),  # для отображения в сваггер
    user_id: Optional[int] = Query(None, example="", alias=USER_ID),
    suspension_service: SuspensionService = Depends(),
    users_service: UsersService = Depends(),
) -> SuspensionAnalytics:
    datetime_start: datetime = datetime.strptime(datetime_start, DATE_TIME_FORMAT)  # обратная конвертация в datetime
    datetime_finish: datetime = datetime.strptime(datetime_finish, DATE_TIME_FORMAT)  # обратная конвертация в datetime
    if user_id is None:
        suspensions = await suspension_service.get_all_for_period_time(datetime_start, datetime_finish)
    else:
        suspensions = await suspension_service.get_suspensions_for_period_for_user(
            user_id, datetime_start, datetime_finish
        )
    suspensions_list = []
    for suspension in suspensions:  # todo это работа сервиса, перенести
        user = await users_service.get(suspension.user_id)  # todo избавиться от дергания базы: загружать за 1 раз
        suspension_to_dict = await change_schema_response(suspension, user)
        suspensions_list.append(suspension_to_dict)
    return SuspensionAnalytics(  # todo аналитику тоже придется перенастроить на использование юзера, или нет
        suspensions_in_mins_total=(
            await suspension_service.sum_suspensions_time_for_period(user_id, datetime_start, datetime_finish)
        ),
        suspensions_total=(
            await suspension_service.count_suspensions_for_period(user_id, datetime_start, datetime_finish)
        ),
        suspension_max_time_for_period=(
            await suspension_service.suspension_max_time_for_period(user_id, datetime_start, datetime_finish)
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
