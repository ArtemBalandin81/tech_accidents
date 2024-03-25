"""src/api/endpoints/tasks.py"""
import structlog

from collections.abc import Sequence
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import PositiveInt, EmailStr

from src.api.constants import *
from src.api.schema import (  # todo change the "schema" to "schemas" after schemas refactoring
    AnalyticTaskResponse,
    TaskResponse,
)
from src.api.services import TaskService, UsersService
from src.core.db.models import User
from src.core.db.user import current_superuser, current_user, unauthorized_user

from src.core.enums import Executor, TechProcess  # todo занеси инструкцию к STAFF в readme

log = structlog.get_logger()
task_router = APIRouter()


@task_router.post(
    TASKS_POST_BY_FORM,
    description=TASK_CREATE_FORM,
    summary=TASK_CREATE_FORM,
    tags=[TASKS_POST]
)
async def create_new_task_by_form(
    *,
    task_start: str = Query(..., example=CREATE_TASK_START, alias=TASK_START),
    deadline: str = Query(..., example=CREATE_TASK_DEADLINE, alias=TASK_FINISH),
    task: str = Query(..., max_length=256, example=TASK_DESCRIPTION, alias=TASK),
    tech_process: TechProcess = Query(..., alias=TECH_PROCESS),
    description: str = Query(..., max_length=256, example=TASK_DESCRIPTION, alias=TASK_DESCRIPTION),
    executor_email: Executor = Query(..., alias=TASK_EXECUTOR_MAIL),
    another_email: Optional[EmailStr] = Query(None, alias=TASK_EXECUTOR_MAIL_NOT_FROM_ENUM),
    task_service: TaskService = Depends(),
    users_service: UsersService = Depends(),
    user: User = Depends(current_user),
) -> AnalyticTaskResponse:
    task_start: date = datetime.strptime(task_start, DATE_FORMAT)  # обратная конвертация в datetime
    deadline: date = datetime.strptime(deadline, DATE_FORMAT)  # обратная конвертация в datetime
    if another_email is not None:
        executor = await users_service.get_by_email(another_email)
    else:
        executor = await users_service.get_by_email(executor_email.value)
    task_object = {
        "task_start": task_start,
        "deadline": deadline,
        "task": task,
        "tech_process": tech_process.value,
        "description": description,
        "executor": executor.id,
    }
    new_task = await task_service.actualize_object(None, task_object, user)
    task = await task_service.perform_changed_schema(new_task)
    return AnalyticTaskResponse(**task[0])


@task_router.patch(
    TASK_ID,
    dependencies=[Depends(current_user)],
    description=TASK_PATCH_FORM,
    summary=TASK_PATCH_FORM,
    tags=[TASKS_POST]
)
async def partially_update_task_by_form(
    task_id: PositiveInt,
    deadline: Optional[str] = Query(
        None,
        example=CREATE_TASK_DEADLINE,
        alias=TASK_FINISH,
        regex=DATE_PATTERN_FORM
    ),
    task: Optional[str] = Query(None, max_length=256, alias=TASK),
    description: Optional[str] = Query(None, max_length=256, alias=TASK_DESCRIPTION),
    is_archived: bool = Query(..., alias=IS_ARCHIVED),
    task_service: TaskService = Depends(),
    user: User = Depends(current_user),
) -> AnalyticTaskResponse:
    task_from_db = await task_service.get(task_id)  # получаем объект из БД и заполняем недостающие поля
    deadline: date = (
        datetime.strptime(deadline, DATE_FORMAT)
        if deadline is not None
        else datetime.strptime(task_from_db.deadline.strftime(DATE_FORMAT), DATE_FORMAT)
    )  # Из БД получаем date -> конвертируем в str -> записываем обратно в БД в datetime для сопоставимости форматов
    task_start: date = datetime.strptime(task_from_db.task_start.strftime(DATE_FORMAT), DATE_FORMAT)
    task_object = {
        "task_start": task_start,
        "deadline": deadline,
        "task": task_from_db.task if task is None else task,
        "tech_process": task_from_db.tech_process,
        "description": task_from_db.description if description is None else description,
        "executor": task_from_db.executor,
        "is_archived": is_archived
    }
    edited_task = await task_service.actualize_object(task_id, task_object, user)
    edited_task_list = await task_service.perform_changed_schema(edited_task)
    return AnalyticTaskResponse(**edited_task_list[0])


@task_router.get(
    GET_ALL_ROUTE,
    response_model_exclude_none=True,
    description=TASK_LIST,
    summary=TASK_LIST,
    tags=[TASKS_GET]
)
async def get_all_tasks(task_service: TaskService = Depends()) -> Sequence[AnalyticTaskResponse]:
    return await task_service.perform_changed_schema(await task_service.get_all())  # noqa


@task_router.get(
    GET_OPENED_ROUTE,
    response_model_exclude_none=True,
    description=TASK_OPENED_LIST,
    summary=TASK_OPENED_LIST,
    tags=[TASKS_GET]
)
async def get_all_opened_tasks(task_service: TaskService = Depends()) -> Sequence[AnalyticTaskResponse]:
    return await task_service.perform_changed_schema(await task_service.get_all_opened())  # noqa


@task_router.get(
    MY_TASKS,
    description=MY_TASKS_LIST,
    summary=MY_TASKS_LIST,
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
    summary=ME_TODO_LIST,
    response_model_exclude_none=True,
    tags=[TASKS_GET]
)
async def get_my_tasks_todo(
    task_service: TaskService = Depends(),
    user: User = Depends(current_user)
) -> Sequence[AnalyticTaskResponse]:
    return await task_service.perform_changed_schema(await task_service.get_my_tasks_todo(user.id))  # noqa


@task_router.get(
    TASK_ID,
    description=TASK_DESCRIPTION,
    summary=TASK_DESCRIPTION,
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
    summary=TASK_DELETE,
    tags=[TASKS_POST]
)
async def remove_task(task_id: int, task_service: TaskService = Depends()) -> None:
    return await task_service.remove(task_id)
