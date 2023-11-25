"""src/api/endpoints/suspensions.py"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.constants import FROM_TIME, FROM_TIME_NOW, TO_TIME, TO_TIME_PERIOD
from src.api.schemas import (
    AnalyticResponse, SuspensionAnalytics, SuspensionRequest, SuspensionResponse
)
from src.api.services import SuspensionService, UsersService
from src.core.db.models import Suspension, User
from src.core.db.user import current_superuser, current_user, unauthorized_user

from src.core.enums import RiskAccidentSource, TechProcess

suspension_router = APIRouter()

ANALYTICS = "/analytics"
ONLY_AUTHOR = "Только автор простоя и админ могут редактировать!"
SUSPENSION_ID = "/{suspension_id}"


async def change_schema_response(suspension: Suspension, user: User) -> AnalyticResponse:
    """Изменяет и добавляет поля в схему ответа создания, запроса по id и аналитики."""
    suspension_to_dict = suspension.__dict__
    suspension_to_dict["user_email"] = user.email
    suspension_to_dict["business_process"] = TechProcess(suspension.tech_process).name
    return AnalyticResponse(**suspension_to_dict)


@suspension_router.post(
    "/form",
    description="Фиксации случая простоя из формы.",
    tags=["Suspensions POST"]
)
async def create_new_suspension_by_form(  # TODO вместо параметров функции использовать класс или еще что-то
    *,
    datetime_start: datetime = Query(..., example=FROM_TIME),
    datetime_finish: datetime = Query(..., example=TO_TIME),
    risk_accident: RiskAccidentSource,
    tech_process: TechProcess,
    description: str = Query(..., max_length=256, example="Кратковременный сбой в работе оборудования."),
    implementing_measures: str = Query(..., max_length=256, example="Перезагрузка оборудования."),
    suspension_service: SuspensionService = Depends(),
    users_service: UsersService = Depends(),
    user: User = Depends(current_user),
) -> AnalyticResponse:
    suspension_object = {  # TODO используй typedict или pydantic suspension_router.get(SUSPENSION_ID
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
    "/",
    response_model=SuspensionResponse,
    description="Фиксации случая простоя из json.",
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
    dependencies=[Depends(current_user)],
    tags=["Suspensions POST"]
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
    "/",
    response_model_exclude_none=True,
    description="Список всех случаев простоя.",
    tags=["Suspensions GET"]
)
async def get_all_suspensions(suspension_service: SuspensionService = Depends()) -> list[SuspensionResponse]:
    return await suspension_service.get_all()


@suspension_router.get(
    ANALYTICS,
    response_model_exclude_none=True,
    description="Список случаев простоя за период.",
    tags=["Suspensions GET"]
)
async def get_all_for_period_time(
    datetime_start: datetime = Query(..., example=FROM_TIME_NOW),
    datetime_finish: datetime = Query(..., example=TO_TIME_PERIOD),
    suspension_service: SuspensionService = Depends(),
    users_service: UsersService = Depends(),
) -> SuspensionAnalytics:
    suspensions = await suspension_service.get_all_for_period_time(datetime_start, datetime_finish)
    suspensions_list = []
    for suspension in suspensions:
        user = await users_service.get(suspension.user_id)  # todo избавиться от дергания базы: грузить за 1 раз
        suspension_to_dict = await change_schema_response(suspension, user)
        suspensions_list.append(suspension_to_dict)
    return SuspensionAnalytics(
        suspensions_in_mins_total=(
            await suspension_service.sum_suspensions_time_for_period(datetime_start, datetime_finish)
        ),
        suspensions_total=await suspension_service.count_suspensions_for_period(datetime_start, datetime_finish),
        max_suspension_time_for_period=(
            await suspension_service.max_suspension_time_for_period(datetime_start, datetime_finish)
        ),
        last_time_suspension=await suspension_service.get_last_suspension_time(),
        last_time_suspension_id=await suspension_service.get_last_suspension_id(),
        # suspensions=suspensions,
        suspensions_detailed=suspensions_list
    )


@suspension_router.get(
    SUSPENSION_ID,
    description="Информация о случае простоя по его id.",
    tags=["Suspensions GET"]
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
    tags=["Suspensions POST"]
)
async def remove_suspension(suspension_id: int, suspension_service: SuspensionService = Depends()) -> None:
    return await suspension_service.remove(suspension_id)
