"""src/api/endpoints/tasks.py"""
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Optional, List, Union, Annotated

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from fastapi.responses import FileResponse
from pydantic import EmailStr, PositiveInt

from src.api.constants import *
from src.api.schema import AddTaskFileResponse, AnalyticTaskResponse  # todo subst to "schemas" after schemas refactoring
from src.api.services import FileService, TaskService, UsersService
from src.core.db.models import Task, User
from src.core.db.user import current_superuser, current_user
from src.core.enums import Executor, TechProcess, ChoiceDownloadFiles
from src.settings import settings

log = structlog.get_logger()
task_router = APIRouter()

SERVICES_DIR = Path(__file__).resolve().parent.parent.parent.parent
FILES_DIR = SERVICES_DIR.joinpath(settings.FILES_DOWNLOAD_DIR)


@task_router.post(
    POST_TASK_FORM,
    description=TASK_CREATE_FORM,
    summary=TASK_CREATE_FORM,
    tags=[TASKS_POST]
)
async def create_new_task_by_form(
    *,
    file_to_upload: UploadFile = None,
    task_start: str = Query(..., example=CREATE_TASK_START, alias=TASK_START),
    deadline: str = Query(..., example=CREATE_TASK_DEADLINE, alias=TASK_FINISH),
    task: str = Query(..., max_length=256, example=TASK_DESCRIPTION, alias=TASK),
    tech_process: TechProcess = Query(..., alias=TECH_PROCESS),
    description: str = Query(..., max_length=256, example=TASK_DESCRIPTION, alias=TASK_DESCRIPTION),
    executor_email: Executor = Query(..., alias=TASK_EXECUTOR_MAIL),
    another_email: Optional[EmailStr] = Query(None, alias=TASK_EXECUTOR_MAIL_NOT_FROM_ENUM),
    file_service: FileService = Depends(),
    task_service: TaskService = Depends(),
    users_service: UsersService = Depends(),
    user: User = Depends(current_user),
) -> AnalyticTaskResponse:
    """Постановка задачи из формы с возможностью загрузки 1 файла."""
    if another_email is not None:
        executor = await users_service.get_by_email(another_email)
    else:
        executor = await users_service.get_by_email(executor_email.value)
    task_object = {
        "task_start": datetime.strptime(task_start, DATE_FORMAT),  # обратная конвертация в datetime
        "deadline": datetime.strptime(deadline, DATE_FORMAT),  # обратная конвертация в datetime,
        "task": task,
        "tech_process": tech_process.value,
        "description": description,
        "executor": executor.id,
    }
    # 1. Записываем задачу в БД, чтобы к ней прикрепить файл впоследствии:
    new_task: Task = await task_service.actualize_object(None, task_object, user)
    task: dict = await task_service.change_schema_response(new_task)
    if file_to_upload is not None:  # 2. Сохраняем файл и вносим о нем записи в таблицы files и tasks_files в БД
        file_timestamp = (datetime.now(TZINFO)).strftime(FILE_DATETIME_FORMAT)  # метка времени в имени файла
        file_names_and_ids: tuple[list[str], list[int]] = await file_service.download_and_write_files_in_db(
            [file_to_upload], FILES_DIR, file_timestamp
        )
        task_id = new_task.id
        file_id = file_names_and_ids[1]
        file_name = file_names_and_ids[0]
        await task_service.set_files_to_task(task_id, file_id)
        await log.ainfo("{}{}{}{}".format(TASK, task_id, FILES_ATTACHED_TO_TASK, file_id))
        task["extra_files"]: list[str] = file_name  # дополняем словарь для ответа AnalyticTaskResponse
    task["extra_files"]: list[str] = []
    return AnalyticTaskResponse(**task)


@task_router.post(
    POST_TASKS_FORM,
    description=TASKS_CREATE_FORM,
    summary=TASKS_CREATE_FORM,
    tags=[TASKS_POST]
)
async def create_new_task_by_form_with_files(
    *,
    files_to_upload: list[UploadFile] = File(...),
    task_start: str = Query(..., example=CREATE_TASK_START, alias=TASK_START),
    deadline: str = Query(..., example=CREATE_TASK_DEADLINE, alias=TASK_FINISH),
    task: str = Query(..., max_length=256, example=TASK_DESCRIPTION, alias=TASK),
    tech_process: TechProcess = Query(..., alias=TECH_PROCESS),
    description: str = Query(..., max_length=256, example=TASK_DESCRIPTION, alias=TASK_DESCRIPTION),
    executor_email: Executor = Query(..., alias=TASK_EXECUTOR_MAIL),
    another_email: Optional[EmailStr] = Query(None, alias=TASK_EXECUTOR_MAIL_NOT_FROM_ENUM),
    file_service: FileService = Depends(),
    task_service: TaskService = Depends(),
    users_service: UsersService = Depends(),
    user: User = Depends(current_user),
) -> AnalyticTaskResponse:
    """Постановка задачи из формы с обязательной загрузкой нескольких файлов."""
    if another_email is not None:
        executor = await users_service.get_by_email(another_email)
    else:
        executor = await users_service.get_by_email(executor_email.value)
    task_object = {
        "task_start": datetime.strptime(task_start, DATE_FORMAT),  # обратная конвертация в datetime
        "deadline": datetime.strptime(deadline, DATE_FORMAT),  # обратная конвертация в datetime,
        "task": task,
        "tech_process": tech_process.value,
        "description": description,
        "executor": executor.id,
    }
    # 1. Записываем задачу в БД, чтобы к ней прикрепить файл впоследствии:
    new_task: Task = await task_service.actualize_object(None, task_object, user)
    task: dict = await task_service.change_schema_response(new_task)
    # if files_to_upload is not None:  # 2. Сохраняем файл и вносим о нем записи в таблицы files и tasks_files в БД
    file_timestamp = (datetime.now(TZINFO)).strftime(FILE_DATETIME_FORMAT)  # метка времени в имени файла
    file_names_and_ids: tuple[list[str], list[int]] = await file_service.download_and_write_files_in_db(
        files_to_upload, FILES_DIR, file_timestamp
    )
    task_id = new_task.id
    files_ids = file_names_and_ids[1]
    files_names = file_names_and_ids[0]
    await task_service.set_files_to_task(task_id, files_ids)
    await log.ainfo("{}{}{}{}".format(TASK, task_id, FILES_ATTACHED_TO_TASK, files_ids))
    task["extra_files"]: list[str] = files_names  # дополняем словарь для ответа AnalyticTaskResponse
    return AnalyticTaskResponse(**task)


@task_router.post(
    ADD_FILES_TO_TASK,
    description=SET_FILES_LIST_TO_TASK,
    summary=SET_FILES_LIST_TO_TASK,
    dependencies=[Depends(current_superuser)],
    tags=[TASKS_POST]
)
async def add_files_to_task(
    *,
    task_id: PositiveInt,
    files_ids: list[PositiveInt] = Query(None, alias=SET_FILES_LIST_TO_TASK),
    task_service: TaskService = Depends(),
) -> AddTaskFileResponse:
    await task_service.set_files_to_task(task_id, files_ids)
    await log.ainfo("{}{}{}{}".format(TASK, task_id, FILES_ATTACHED_TO_TASK, files_ids))
    return AddTaskFileResponse(task_id=task_id, files_ids=files_ids)


@task_router.patch(  #todo здесь также нужно предусмотреть добавление файлов - опять сервис единый, чтобы не дублиров
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


@task_router.get(  # todo сейчас ошибка. связанная со схемой AnalyticTaskResponse (требуются файлы)
    GET_ALL_ROUTE,
    response_model_exclude_none=True,
    description=TASK_LIST,
    summary=TASK_LIST,
    tags=[TASKS_GET]
)
async def get_all_tasks(task_service: TaskService = Depends()) -> Sequence[AnalyticTaskResponse]:
    return await task_service.perform_changed_schema(await task_service.get_all())  # noqa


@task_router.get(  # todo сейчас ошибка. связанная со схемой AnalyticTaskResponse (требуются файлы)
    GET_OPENED_ROUTE,
    response_model_exclude_none=True,
    description=TASK_OPENED_LIST,
    summary=TASK_OPENED_LIST,
    tags=[TASKS_GET]
)
async def get_all_opened_tasks(task_service: TaskService = Depends()) -> Sequence[AnalyticTaskResponse]:
    return await task_service.perform_changed_schema(await task_service.get_all_opened())  # noqa


@task_router.get(  # todo сейчас ошибка. связанная со схемой AnalyticTaskResponse (требуются файлы)
    MY_TASKS,
    description=MY_TASKS_LIST,
    summary=MY_TASKS_LIST,
    response_model_exclude_none=True,
    tags=[TASKS_GET]
)
async def get_my_tasks_ordered(  # todo сейчас ошибка. связанная со схемой AnalyticTaskResponse (требуются файлы)
    task_service: TaskService = Depends(),
    user: User = Depends(current_user)
) -> Sequence[AnalyticTaskResponse]:
    return await task_service.perform_changed_schema(await task_service.get_tasks_ordered(user.id))  # noqa


@task_router.get(  # todo сейчас ошибка. связанная со схемой AnalyticTaskResponse (требуются файлы)
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
    response_model=None,  # Invalid args for response field -> response_model=None
    dependencies=[Depends(current_user)],
    description=TASK_DESCRIPTION,
    summary=TASK_DESCRIPTION,
    tags=[TASKS_GET]
)
async def get_task_by_id(
    task_id: PositiveInt,
    choice_download_files: ChoiceDownloadFiles = Query(..., alias=CHOICE_FORMAT),
    task_service: TaskService = Depends(),
    file_service: FileService = Depends()
) -> AnalyticTaskResponse | Response:  # Invalid args for response field -> response_model=None
    task: dict = await task_service.change_schema_response(await task_service.get(task_id))
    files_ids = await task_service.get_file_ids_from_task(task_id)
    files_download_true = settings.CHOICE_DOWNLOAD_FILES.split('"')[-2]  # защита на случай изменений в enum-классе
    if choice_download_files == files_download_true:
        files_to_zip = []
        if len(files_ids) == 0:
            await log.aerror(NOT_FOUND)
            raise HTTPException(status_code=403, detail="{}".format(NOT_FOUND))
        else:
            for file_id in files_ids:  # todo перенести в сервисы файлов - лишняя нагрузка на эндпоинт
                file_db = await file_service.get(file_id)
                files_to_zip.append(FILES_DIR.joinpath(file_db.name))
        return await file_service.zip_files(files_to_zip)
    else:
        files_names = await task_service.get_file_names_from_task(task_id)
        if len(files_ids) != len(files_names):
            tasks_files_mismatch = "{}{}{}{}{}".format(TASK, task_id, TASKS_FILES_MISMATCH, files_ids, files_names)
            await log.aerror(tasks_files_mismatch)
            raise HTTPException(status_code=206, detail=tasks_files_mismatch)
        await log.ainfo("{}{}{}{}{}".format(TASK, task_id, FILES_ATTACHED_TO_TASK, files_ids, files_names))
        task["extra_files"] = files_names
        return AnalyticTaskResponse(**task)


@task_router.delete(  # todo выводить список всех задач в качестве response - сначала поправить отображение файлов
    TASK_ID,
    description=TASK_DELETE,
    dependencies=[Depends(current_superuser)],
    summary=TASK_DELETE,
    tags=[TASKS_POST]
)
async def remove_task(task_id: PositiveInt, task_service: TaskService = Depends()) -> None:
    await task_service.remove(task_id)
    await task_service.set_files_to_task(task_id, [])
    await log.ainfo("{}{}{}".format(TASK, task_id, DELETED_OK))
    await log.ainfo("{}{}{}{}".format(TASK, task_id, FILES_ATTACHED_TO_TASK, []))
