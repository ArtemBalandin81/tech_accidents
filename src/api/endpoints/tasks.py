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
    task = await task_service.perform_changed_schema(task)
    return AnalyticTaskResponse(**task[0])


# @task_router.patch(  # todo сделать в форм: пустые поля, значит не меняем!
#     TASK_ID,
#     dependencies=[Depends(current_user)],
#     tags=[TASKS_POST]
# )
# async def partially_update_task(
#     suspension_id: int,
#     suspension_schemas: SuspensionRequest,
#     suspension_service: SuspensionService = Depends(),
#     users_service: UsersService = Depends(),
#     user: User = Depends(current_user),
# ) -> AnalyticResponse:
#     suspension = await suspension_service.get(suspension_id)  # проверяем, что объект для правки существует!
#     if user.id != suspension.user_id and user.is_superuser is not True:
#         raise HTTPException(status_code=403, detail=ONLY_AUTHOR)
#     await suspension_service.actualize_object(suspension_id, suspension_schemas, user)
#     suspension = await suspension_service.get(suspension_id)
#     user = await users_service.get(suspension.user_id)
#     return await change_schema_response(suspension, user)


@task_router.get(
    GET_ALL_ROUTE,
    response_model_exclude_none=True,
    description=TASK_LIST,
    tags=[TASKS_GET]
)
async def get_all_tasks(task_service: TaskService = Depends()) -> Sequence[AnalyticTaskResponse]:
    return await task_service.perform_changed_schema(await task_service.get_all())  # noqa


@task_router.get(
    GET_OPENED_ROUTE,
    response_model_exclude_none=True,
    description=TASK_LIST,
    tags=[TASKS_GET]
)
async def get_all_opened_tasks(task_service: TaskService = Depends()) -> Sequence[AnalyticTaskResponse]:
    return await task_service.perform_changed_schema(await task_service.get_all_opened())  # noqa


@task_router.get(
    MY_TASKS,
    description=MY_TASKS_LIST,
    response_model_exclude_none=True,
    tags=[TASKS_GET]
)
async def get_my_tasks_ordered(
    task_service: TaskService = Depends(),
    user: User = Depends(current_user)
) -> Sequence[AnalyticTaskResponse]:
    return await task_service.perform_changed_schema(await task_service.get_tasks_ordered(user.id))  # noqa


@task_router.get(
    ME_TODO,
    description=ME_TODO_LIST,
    response_model_exclude_none=True,
    tags=[TASKS_GET]
)
async def get_my_tasks_todo(
    task_service: TaskService = Depends(),
    user: User = Depends(current_user)
) -> Sequence[AnalyticTaskResponse]:    # todo показывать e-mail исполнитяля в схеме
    return await task_service.perform_changed_schema(await task_service.get_my_tasks_todo(user.id))  # noqa


@task_router.get(
    TASK_ID,
    description=TASK_DESCRIPTION,
    tags=[TASKS_GET]
)
async def get_task_by_id(
        task_id: int,
        task_service: TaskService = Depends(),
) -> AnalyticTaskResponse:
    task = await task_service.perform_changed_schema(await task_service.get(task_id))
    return AnalyticTaskResponse(**task[0])


@task_router.delete(
    TASK_ID,
    description=TASK_DELETE,
    dependencies=[Depends(current_superuser)],
    tags=[TASKS_POST]
)
async def remove_task(task_id: int, task_service: TaskService = Depends()) -> None:
    return await task_service.remove(task_id)
