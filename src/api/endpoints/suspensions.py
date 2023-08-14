"""src/api/endpoints/suspensions.py"""
from fastapi import APIRouter, Depends

from src.api.schemas import SuspensionRequest, SuspensionResponse
from src.api.services import SuspensionService
#from src.api.services.messages import TelegramNotificationService
from src.core.db.models import Suspension

suspension_router = APIRouter()


# @task_router.post("/", description="Актуализирует список задач.")
# async def actualize_tasks(
#     tasks: list[TaskRequest],
#     task_service: TaskService = Depends(),
#     telegram_notification_service: TelegramNotificationService = Depends(),
# ) -> None:
#     new_tasks_ids = await task_service.actualize_objects(tasks, Task)
#     new_category_tasks = await task_service.get_user_tasks_ids(new_tasks_ids)
#     for task in new_category_tasks:
#         message = display_tasks(task)
#         await telegram_notification_service.send_messages_to_subscribed_users(message, task.category_id)


# @task_router.get(
#     "/{user_id}",
#     response_model=list[TaskResponse],
#     response_model_exclude_none=True,
#     description="Получает список всех задач из категорий на которые подписан юзер.",
# )
# async def get_tasks_for_user(user_id: int, task_service: TaskService = Depends()) -> list[TaskResponse]:
#     return await task_service.get_tasks_for_user(user_id)


@suspension_router.get(
    "/",
    response_model=list[SuspensionResponse],
    response_model_exclude_none=True,
    description="Получает список всех простоев.",
)
async def get_all_suspensions(suspension_service: SuspensionService = Depends()) -> list[SuspensionResponse]:
    return await suspension_service.get_all()
