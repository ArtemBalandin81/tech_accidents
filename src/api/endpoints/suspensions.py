"""src/api/endpoints/suspensions.py"""
import json
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query, Request

from src.api.constants import FROM_TIME, FROM_TIME_NOW, TO_TIME, TO_TIME_PERIOD
from src.api.schemas import SuspensionAnalytics, SuspensionRequest, SuspensionResponse
from src.api.services import SuspensionService
#from src.api.services.messages import TelegramNotificationService # TODO Для будущего телеграмм
from src.core.db.models import Suspension, User
from src.core.db.user import current_superuser, current_user, unauthorized_user

from src.core.enums import RiskAccidentSource, TechProcess

suspension_router = APIRouter()

SUSPENSION_ID = "/{suspension_id}"
ANALYTICS = "/analytics"
IN_MINS = 60 * 24

@suspension_router.post(
    "/form",
    response_model=SuspensionResponse,
    response_model_exclude_none=True,
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
    # telegram_notification_service: TelegramNotificationService = Depends(), # TODO Для будущего телеграмм
    user: User = Depends(current_user),
    request: Request,
) -> SuspensionResponse:
    suspension_object = {  # TODO используй typedict
        "datetime_start": datetime_start,
        "datetime_finish": datetime_finish,
        "risk_accident": risk_accident,
        "tech_process": tech_process,
        "description": description,
        "implementing_measures": implementing_measures,
    }
    return await suspension_service.actualize_object(None, suspension_object, user)


@suspension_router.post(
    "/",
    response_model=SuspensionResponse,
    description="Фиксации случая простоя из json.",
    tags=["Suspensions POST"]
)
async def create_new_suspension(
    suspension_schemas: SuspensionRequest,
    suspension_service: SuspensionService = Depends(),
    # telegram_notification_service: TelegramNotificationService = Depends(), # TODO Для будущего телеграмм
    user: User = Depends(current_user),
) -> SuspensionResponse:
    return await suspension_service.actualize_object(None, suspension_schemas, user)


@suspension_router.patch(
    SUSPENSION_ID,
    response_model={},
    dependencies=[Depends(current_superuser)],
    tags=["Suspensions POST"]
)
async def partially_update_suspension(
    suspension_id: int,
    suspension_schemas: SuspensionRequest,
    suspension_service: SuspensionService = Depends(),
    user: User = Depends(current_user),
):
    return await suspension_service.actualize_object(suspension_id, suspension_schemas, user)


@suspension_router.get(
    "/",
    response_model=list[SuspensionResponse],
    response_model_exclude_none=True,
    description="Получает список всех простоев.",
    tags=["Suspensions GET"]
)
async def get_all_suspensions(suspension_service: SuspensionService = Depends()) -> list[SuspensionResponse]:
    return await suspension_service.get_all()

@suspension_router.get(
    ANALYTICS,
    response_model_exclude_none=True,
    description="Получает список всех простоев за определенный период времени, интервал.",
    tags=["Suspensions GET"]
)
async def get_all_for_period_time(
        datetime_start: datetime = Query(..., example=FROM_TIME_NOW),
        datetime_finish: datetime = Query(..., example=TO_TIME_PERIOD),
        suspension_service: SuspensionService = Depends()
) -> SuspensionAnalytics:
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
        suspensions=await suspension_service.get_all_for_period_time(datetime_start, datetime_finish)
    )


@suspension_router.get(
    SUSPENSION_ID,
    response_model=SuspensionResponse,
    response_model_exclude_none=True,
    description="Получает случай простоя по его id.",
    tags=["Suspensions GET"]
)
async def get_suspension_by_id(
        suspension_id: int, suspension_service: SuspensionService = Depends()
) -> Suspension:
    return await suspension_service.get(suspension_id)


@suspension_router.delete(
    SUSPENSION_ID,
    #response_model=SuspensionResponse,
    dependencies=[Depends(current_superuser)],
    tags=["Suspensions POST"]
)
async def remove_suspension(suspension_id: int, suspension_service: SuspensionService = Depends()) -> None:
    return await suspension_service.remove(suspension_id)
