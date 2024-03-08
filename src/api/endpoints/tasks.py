"""src/api/endpoints/tasks.py"""
import requests
import structlog

from collections.abc import Sequence
from datetime import datetime, date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.constants import *
from src.api.schema import (  # todo change the name to schemas afterwards
    AnalyticTaskResponse,
    TaskResponse,
)
from src.api.services import TaskService, UsersService
from src.core.db.models import Task, User
from src.core.db.user import current_superuser, current_user, unauthorized_user

from src.core.enums import Executor, RiskAccidentSource, TechProcess

# log = structlog.get_logger()
task_router = APIRouter()


async def change_schema_response(task: Task, user: User, executor: User) -> AnalyticTaskResponse:
    """Изменяет и добавляет поля в схему ответа создания, запроса по id и аналитики."""
    task_to_dict = task.__dict__  # todo криво, поменяй метод, метод дублируется
    task_to_dict["user_email"] = user.email
    task_to_dict["executor_email"] = executor.email
    task_to_dict["business_process"] = TechProcess(task.tech_process).name
    return AnalyticTaskResponse(**task_to_dict)

@task_router.post(
    TASKS_POST_BY_FORM,
    description=TASK_CREATE_FORM,
    tags=[TASKS_POST]
)
async def create_new_task_by_form(
    *,
    task_start: str = Query(..., example=CREATE_TASK_START, alias=TASK_START),
    deadline: str = Query(..., example=CREATE_TASK_DEADLINE, alias=TASK_FINISH),
    task: str = Query(..., max_length=256, example=TASK_DESCRIPTION, alias=TASK),
    tech_process: TechProcess,
    description: str = Query(..., max_length=256, example=TASK_DESCRIPTION, alias=TASK_DESCRIPTION),
    executor_email: Executor,
    task_service: TaskService = Depends(),
    users_service: UsersService = Depends(),
    user: User = Depends(current_user),
) -> AnalyticTaskResponse:
    task_start: date = datetime.strptime(task_start, DATE_FORMAT)  # обратная конвертация в datetime
    deadline: date = datetime.strptime(deadline, DATE_FORMAT)  # обратная конвертация в datetime
    executor = await users_service.get_by_email(executor_email)
    task_object = {
        "task_start": task_start,
        "deadline": deadline,
        "task": task,
        "tech_process": tech_process,
        "description": description,
        "executor": executor.id,
    }
    task = await task_service.actualize_object(None, task_object, user)
    user = await users_service.get(task.user_id)
    executor = await users_service.get(task.executor)  # todo после правки моделей поменять на executor_id
    return await change_schema_response(task, user, executor)


@task_router.get(
    GET_ALL_ROUTE,
    response_model_exclude_none=True,
    description=TASK_LIST,
    tags=[TASKS_GET]
)
async def get_all_tasks(task_service: TaskService = Depends()) -> list[TaskResponse]:
# async def get_all_tasks(task_service: TaskService = Depends()):
    return await task_service.get_all()


# @task_router.get(
#     TASK_ID,
#     description=TASK_DESCRIPTION,
#     tags=["Tasks GET"]
# )
# async def get_task_by_id(
#         task_id: int,
#         task_service: TaskService = Depends(),
#         users_service: UsersService = Depends(),
# ) -> TaskResponse:
#     task = await task_service.get(task_id)
#     user = await users_service.get(task.user_id)
#     return await change_schema_response(suspension, user)


@task_router.delete(
    TASK_ID,
    description=TASK_DELETE,
    dependencies=[Depends(current_superuser)],
    tags=[TASKS_POST]
)
async def remove_task(task_id: int, task_service: TaskService = Depends()) -> None:
    return await task_service.remove(task_id)
