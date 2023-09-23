"""src/api/endpoints/suspensions.py"""
import json
from datetime import datetime
from fastapi import APIRouter, Depends, Query, Request

from src.api.constants import DATE_TIME_FORMAT, FROM_TIME, TO_TIME
from src.api.schemas import SuspensionRequest, SuspensionResponse
from src.api.services import SuspensionService
#from src.api.services.messages import TelegramNotificationService # TODO Для будущего телеграмм
from src.core.db.models import Suspension, User
from src.core.db.user import current_superuser, current_user, unauthorized_user

from src.core.enums import RiskAccidentSource, TechProcess

suspension_router = APIRouter()

SUSPENSION_ID = "/{suspension_id}"

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
    suspension_object = {
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
    response_model=SuspensionResponse,  # TODO Сделать схему для ответа!!!
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


@suspension_router.patch(  # TODO подготовить обновление случая риска по айди
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


@suspension_router.get(  # TODO Эндпоинт для единичного случая риска
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
