"""src/api/endpoints/tasks.py"""
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from pydantic import EmailStr, PositiveInt

from src.api.constants import *
from src.api.schema import AddTaskFileResponse, AnalyticTaskResponse, TaskBase  # todo subst to "schemas" refactoring
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
    task_response: dict = await task_service.change_schema_response(new_task)
    if file_to_upload is None:  # 2. Сохраняем файл и вносим о нем записи в таблицы files и tasks_files в БД
        return AnalyticTaskResponse(**task_response)
    file_timestamp = (datetime.now(TZINFO)).strftime(FILE_DATETIME_FORMAT)  # метка времени в имени файла
    file_names_and_ids: tuple[list[str], list[PositiveInt]] = await file_service.download_and_write_files_in_db(
        [file_to_upload], FILES_DIR, file_timestamp
    )
    task_id = new_task.id
    file_id = file_names_and_ids[1]
    file_name = file_names_and_ids[0]
    await task_service.set_files_to_task(task_id, file_id)
    await log.ainfo("{}{}{}{}".format(TASK, task_id, FILES_ATTACHED_TO_TASK, file_id))
    task_response["extra_files"]: list[str] = file_name  # дополняем словарь для ответа AnalyticTaskResponse
    return AnalyticTaskResponse(**task_response)


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
    file_timestamp = (datetime.now(TZINFO)).strftime(FILE_DATETIME_FORMAT)  # метка времени в имени файла
    file_names_and_ids: tuple[list[str], list[PositiveInt]] = await file_service.download_and_write_files_in_db(
        files_to_upload, FILES_DIR, file_timestamp
    )
    task_id = new_task.id
    files_ids = file_names_and_ids[1]
    await task_service.set_files_to_task(task_id, files_ids)
    await log.ainfo("{}{}{}{}".format(TASK, task_id, FILES_ATTACHED_TO_TASK, files_ids))
    task_response: dict = await task_service.change_schema_response(new_task)
    task_response["extra_files"]: list[str] = file_names_and_ids[0]
    return AnalyticTaskResponse(**task_response)


@task_router.post(
    ADD_FILES_TO_TASK,
    description=SET_FILES_LIST_TO_TASK,
    summary=SET_FILES_LIST_TO_TASK,
    dependencies=[Depends(current_superuser)],
    tags=[TASKS_POST]
)
async def set_files_to_task(
    *,
    task_id: PositiveInt,
    files_ids: list[PositiveInt] = Query(None, alias=SET_FILES_LIST_TO_TASK),
    task_service: TaskService = Depends(),
) -> AddTaskFileResponse:
    """Прикрепление файлов к задаче (запись отношения в БД) (только админ)."""
    await task_service.set_files_to_task(task_id, files_ids)
    await log.ainfo("{}{}{}{}".format(TASK, task_id, FILES_ATTACHED_TO_TASK, files_ids))
    return AddTaskFileResponse(task_id=task_id, files_ids=files_ids)


@task_router.patch(  #todo здесь также нужно предусмотреть добавление файлов - опять сервис единый, чтобы не дублировал
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
        description=CREATE_TASK_DEADLINE,
        alias=TASK_FINISH,
        regex=DATE_PATTERN_FORM
    ),
    task: Optional[str] = Query(None, max_length=256, alias=TASK),
    description: Optional[str] = Query(None, max_length=256, alias=TASK_DESCRIPTION),
    is_archived: bool = Query(None, alias=IS_ARCHIVED),
    tech_process: TechProcess = Query(None, alias=TECH_PROCESS),
    executor_email: Executor = Query(None, alias=TASK_EXECUTOR_MAIL),
    file_to_upload: UploadFile = None,
    to_unlink_files: bool = Query(None, alias=TASK_FILES_UNLINK),
    task_service: TaskService = Depends(),
    users_service: UsersService = Depends(),
    file_service: FileService = Depends(),
    user: User = Depends(current_user),
) -> AnalyticTaskResponse:
    task_from_db = await task_service.get(task_id)  # получаем объект из БД и заполняем недостающие поля
    deadline: date = (
        datetime.strptime(str(deadline), DATE_FORMAT)
        if deadline is not None
        else datetime.strptime(task_from_db.deadline.strftime(DATE_FORMAT), DATE_FORMAT)
    )  # Из БД получаем date -> конвертируем в str -> записываем обратно в БД в datetime для сопоставимости форматов
    task_start: date = datetime.strptime(task_from_db.task_start.strftime(DATE_FORMAT), DATE_FORMAT)
    executor = await users_service.get_by_email(executor_email.value) if executor_email is not None else None
    task_object = {
        "task_start": task_start,
        "deadline": deadline,
        "task": task_from_db.task if task is None else task,
        "tech_process": task_from_db.tech_process if tech_process is None else tech_process,
        "description": task_from_db.description if description is None else description,
        "executor": task_from_db.executor if executor_email is None else executor.id,  # noqa
        "is_archived": task_from_db.is_archived if is_archived is None else is_archived
    }
    edited_task = await task_service.actualize_object(task_id, task_object, user)
    edited_task_response: Sequence[dict] = await task_service.perform_changed_schema(edited_task)
    if to_unlink_files and file_to_upload is not None:
        await log.aerror("{}".format(TASKS_FILES_REMOVE_AND_SET))
        raise HTTPException(status_code=406, detail="{}".format(TASKS_FILES_REMOVE_AND_SET))
    if to_unlink_files:
        file_names_and_ids_set_to_task: tuple[list[str], list[PositiveInt]] = (
            await task_service.get_file_names_and_ids_from_task(task_id)
        )
        await task_service.set_files_to_task(task_id, [])
        edited_task_response[0]["extra_files"]: list[str] = []
        if file_names_and_ids_set_to_task[1] is not None:
            await file_service.remove_files(file_names_and_ids_set_to_task[1], FILES_DIR)
            await log.ainfo("{}{}{}{}{}{}".format(
                TASK_PATCH_FORM, task_id, SPACE, FILES_SET_TO, file_names_and_ids_set_to_task[0], DELETED_OK)
            )
        await log.ainfo("{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}".format(
            TASK_PATCH_FORM, task_id, SPACE, TASK, task, SPACE, TASK_DESCRIPTION, description, SPACE, IS_ARCHIVED,
            SPACE, is_archived, SPACE, TECH_PROCESS, tech_process, SPACE, TASK_FINISH, deadline, SPACE, TASK_EXECUTOR,
            executor_email, SPACE, FILES_ATTACHED_TO_TASK, [],)
        )
        return AnalyticTaskResponse(**edited_task_response[0])
    if file_to_upload is not None:  # 2. Сохраняем файл и вносим о нем записи в таблицы files и tasks_files в БД
        file_timestamp = (datetime.now(TZINFO)).strftime(FILE_DATETIME_FORMAT)  # метка времени в имени файла
        file_names_and_ids_attached: tuple[list[str], list[PositiveInt]] = (
            await file_service.download_and_write_files_in_db(
                [file_to_upload], FILES_DIR, file_timestamp)
        )
        new_file_id = file_names_and_ids_attached[1]
        new_file_name = file_names_and_ids_attached[0]
        file_names_and_ids_set_to_task: tuple[list[str], list[PositiveInt]] = (
            await task_service.get_file_names_and_ids_from_task(task_id)
        )
        new_file_ids = new_file_id + file_names_and_ids_set_to_task[1]
        new_file_names = new_file_name + file_names_and_ids_set_to_task[0]
        await task_service.set_files_to_task(task_id, new_file_ids)
        edited_task_response[0]["extra_files"]: list[str] = new_file_names  # дополняем словарь AnalyticTaskResponse
        await log.ainfo("{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}".format(
            TASK_PATCH_FORM, task_id, SPACE, TASK, task, SPACE, TASK_DESCRIPTION, description, SPACE, IS_ARCHIVED,
            SPACE, is_archived, SPACE, TECH_PROCESS, tech_process, SPACE, TASK_FINISH, deadline, SPACE, TASK_EXECUTOR,
            executor_email, SPACE, FILES_ATTACHED_TO_TASK, new_file_id, SPACE, new_file_name, SPACE, FILES_SET_TO,
            new_file_ids, new_file_names)
        )
        return AnalyticTaskResponse(**edited_task_response[0])
    await log.ainfo("{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}".format(
        TASK_PATCH_FORM, task_id, SPACE, TASK, task, SPACE, TASK_DESCRIPTION, description, SPACE, IS_ARCHIVED, SPACE,
        is_archived, SPACE, TECH_PROCESS, tech_process, SPACE, TASK_FINISH, deadline, SPACE, TASK_EXECUTOR,
        executor_email)
    )
    return AnalyticTaskResponse(**edited_task_response[0])


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
    file_ids: Sequence[PositiveInt] = await task_service.get_file_ids_from_task(task_id)
    files_download_true = settings.CHOICE_DOWNLOAD_FILES.split('"')[-2]  # защита на случай изменений в enum-классе
    if choice_download_files == files_download_true:
        if len(file_ids) == 0:
            await log.aerror(NOT_FOUND)
            raise HTTPException(status_code=403, detail="{}".format(NOT_FOUND))
        else:
            return await file_service.zip_files(await file_service.prepare_files_to_work_with(file_ids, FILES_DIR))
    else:
        task: Sequence[dict] = await task_service.perform_changed_schema(await task_service.get(task_id))
        return AnalyticTaskResponse(**task[0])


@task_router.delete(  # todo удалять также и сами файлы физически из папки
    TASK_ID,
    description=TASK_DELETE,
    dependencies=[Depends(current_superuser)],
    summary=TASK_DELETE,
    tags=[TASKS_POST]
)
async def remove_task(
        task_id: PositiveInt,
        file_service: FileService = Depends(),
        task_service: TaskService = Depends()
) -> Sequence[TaskBase]:
    files_ids_set_to_task: Sequence[int] = await task_service.get_file_ids_from_task(task_id)
    if files_ids_set_to_task:
        files_to_delete: Sequence[Path] = await file_service.prepare_files_to_work_with(
            files_ids_set_to_task, FILES_DIR
        )
        await file_service.delete_files_in_folder(files_to_delete)
        await log.ainfo("{}{}{}{}{}{}".format(TASK, task_id, SPACE, FILES_SET_TO, files_to_delete, DELETED_OK))
    actual_tasks = await task_service.remove(task_id)
    await task_service.set_files_to_task(task_id, [])
    await log.ainfo("{}{}{}".format(TASK, task_id, DELETED_OK))
    await log.ainfo("{}{}{}{}".format(TASK, task_id, FILES_ATTACHED_TO_TASK, []))
    return actual_tasks  # noqa
