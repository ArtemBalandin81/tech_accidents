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


# TODO подготовить обновление случая риска по айди

@suspension_router.post(
    "/form",
    #response_model=SuspensionResponse,  # TODO Сделать схему для ответа!!!
    description="Фиксации случая простоя из формы."
)
async def create_form_new_suspension(  # TODO вместо параметров функции использовать класс или еще что-то
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
) -> None:
    suspension_object = {
        "datetime_start": datetime_start,
        "datetime_finish": datetime_finish,
        "risk_accident": risk_accident,
        "tech_process": tech_process,
        "description": description,
        "implementing_measures": implementing_measures,
    }
    await suspension_service.actualize_object(suspension_object, user)



@suspension_router.post(
    "/",
    #response_model=SuspensionResponse,  # TODO Сделать схему для ответа!!!
    description="Фиксации случая простоя из json."
)
async def create_new_suspension(
    suspension_schemas: SuspensionRequest,
    suspension_service: SuspensionService = Depends(),
    # telegram_notification_service: TelegramNotificationService = Depends(), # TODO Для будущего телеграмм
    user: User = Depends(current_user),
) -> None:
    await suspension_service.actualize_object(suspension_schemas, user)


@suspension_router.get(
    "/",
    response_model=list[SuspensionResponse],
    response_model_exclude_none=True,
    description="Получает список всех простоев.",
)
async def get_all_suspensions(suspension_service: SuspensionService = Depends()) -> list[SuspensionResponse]:
    return await suspension_service.get_all()


# @task_router.get(  # TODO Эндпоинт для единичного случая риска
#     "/{user_id}",
#     response_model=list[TaskResponse],
#     response_model_exclude_none=True,
#     description="Получает список всех задач из категорий на которые подписан юзер.",
# )
# async def get_tasks_for_user(user_id: int, task_service: TaskService = Depends()) -> list[TaskResponse]:
#     return await task_service.get_tasks_for_user(user_id)
