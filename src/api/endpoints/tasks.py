"""src/api/endpoints/tasks.py"""
import requests
import structlog

from collections.abc import Sequence
from datetime import datetime, date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.constants import *
from src.api.schema import (  # todo change the "schema" to "schemas" after schemas refactoring
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
async def get_all_tasks(task_service: TaskService = Depends()) -> Sequence[TaskResponse]:
    return await task_service.get_all()


@task_router.get(
    GET_OPENED_ROUTE,
    response_model_exclude_none=True,
    description=TASK_LIST,
    tags=[TASKS_GET]
)
async def get_all_opened_tasks(task_service: TaskService = Depends()) -> Sequence[TaskResponse]:
    return await task_service.get_all_opened()


@task_router.get(
    MY_TASKS,
    description=MY_TASKS_LIST,
    response_model_exclude_none=True,
    tags=[TASKS_GET]
)
async def get_my_tasks_ordered(
    task_service: TaskService = Depends(),
    user: User = Depends(current_user)
) -> Sequence[TaskResponse]:    # todo показывать e-mail исполнитяля в схеме
    return await task_service.get_tasks_ordered(user.id)


@task_router.get(
    ME_TODO,
    description=ME_TODO_LIST,
    response_model_exclude_none=True,
    tags=[TASKS_GET]
)
async def get_my_tasks_todo(
    task_service: TaskService = Depends(),
    user: User = Depends(current_user)
) -> Sequence[TaskResponse]:    # todo показывать e-mail исполнитяля в схеме
    return await task_service.get_my_tasks_todo(user.id)


@task_router.get(
    TASK_ID,
    description=TASK_DESCRIPTION,
    tags=[TASKS_GET]
)
async def get_task_by_id(
        task_id: int,
        task_service: TaskService = Depends(),
        users_service: UsersService = Depends(),
) -> AnalyticTaskResponse:
    task = await task_service.get(task_id)
    user = await users_service.get(task.user_id)
    executor = await users_service.get(task.executor)  # todo после правки моделей поменять на executor_id
    return await change_schema_response(task, user, executor)


@task_router.delete(
    TASK_ID,
    description=TASK_DELETE,
    dependencies=[Depends(current_superuser)],
    tags=[TASKS_POST]
)
async def remove_task(task_id: int, task_service: TaskService = Depends()) -> None:
    return await task_service.remove(task_id)
