"""src/api/endpoints/tasks.py"""
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, File, Query, Response, UploadFile
from pydantic import EmailStr, PositiveInt
from src.api.constants import *
from src.api.schema import (AnalyticTaskResponse, TaskCreate,  # todo "schemas"
                            TaskDeletedResponse, TaskResponse)
from src.api.services import FileService, TaskService, UsersService
from src.api.validators import (
    check_exist_files_attached,
    check_not_download_and_delete_files_at_one_time,
    check_same_files_not_to_download, check_start_not_exceeds_finish)
from src.core.db.models import Task, User
from src.core.db.user import current_superuser, current_user
from src.core.enums import ChoiceDownloadFiles, Executor, TechProcess
from src.settings import settings

log = structlog.get_logger()
task_router = APIRouter()

SERVICES_DIR = Path(__file__).resolve().parent.parent.parent.parent  # move to settings todo
FILES_DIR = SERVICES_DIR.joinpath(settings.FILES_DOWNLOAD_DIR)  # move to settings todo


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
    await check_start_not_exceeds_finish(task_start, deadline, DATE_FORMAT)
    if another_email is not None:
        executor = await users_service.get_by_email(another_email)
    else:
        executor = await users_service.get_by_email(executor_email.value)
    task_object = {
        "task_start": datetime.strptime(task_start, DATE_FORMAT),  # reverse in datetime
        "deadline": datetime.strptime(deadline, DATE_FORMAT),  # reverse in datetime
        "task": task,
        "tech_process": tech_process.value,
        "description": description,
        "executor_id": executor.id,
    }
    # 1. Write task in db with pydantic (without attached_files).
    new_task: Task = await task_service.actualize_object(None, TaskCreate(**task_object), user)
    task_response: dict = await task_service.change_schema_response(new_task, user, executor)
    if file_to_upload is None:
        return AnalyticTaskResponse(**task_response)
    # 2. Download and write files in db and make records in tables "files" & "tasks_files" in db:
    file_timestamp = (datetime.now(TZINFO)).strftime(FILE_DATETIME_FORMAT)  # timestamp in filename
    file_names_and_ids: tuple[list[str], list[PositiveInt]] = await file_service.download_and_write_files_in_db(
        [file_to_upload], FILES_DIR, file_timestamp
    )
    task_id = new_task.id
    file_id = file_names_and_ids[1]
    file_name = file_names_and_ids[0]
    await task_service.set_files_to_task(task_id, file_id)
    await log.ainfo("{}".format(FILES_ATTACHED_TO_TASK), task_id=task_id, file_id=file_id, file_name=file_name)
    task_response["extra_files"]: list[str] = file_name  # add dictionary for AnalyticTaskResponse
    return AnalyticTaskResponse(**task_response)


@task_router.post(
    POST_TASK_FILES_FORM,
    description=TASK_FILES_CREATE_FORM,
    summary=TASK_FILES_CREATE_FORM,
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
    await check_start_not_exceeds_finish(task_start, deadline, DATE_FORMAT)
    await check_same_files_not_to_download(files_to_upload)
    if another_email is not None:
        executor = await users_service.get_by_email(another_email)
    else:
        executor = await users_service.get_by_email(executor_email.value)
    task_object = {
        "task_start": datetime.strptime(task_start, DATE_FORMAT),  # reverse in datetime
        "deadline": datetime.strptime(deadline, DATE_FORMAT),  # reverse in datetime
        "task": task,
        "tech_process": tech_process.value,
        "description": description,
        "executor_id": executor.id,
    }
    new_task: Task = await task_service.actualize_object(None, TaskCreate(**task_object), user)  # 1. Write task in db
    # 2. Download and write files in db and make records in tables "files" & "tasks_files" in db:
    file_timestamp = (datetime.now(TZINFO)).strftime(FILE_DATETIME_FORMAT)  # timestamp in filename
    file_names_and_ids: tuple[list[str], list[PositiveInt]] = await file_service.download_and_write_files_in_db(
        files_to_upload, FILES_DIR, file_timestamp
    )
    task_id = new_task.id
    files_ids = file_names_and_ids[1]
    files_names = file_names_and_ids[0]
    await task_service.set_files_to_task(task_id, files_ids)
    await log.ainfo(
        "{}{}{}".format(TASK, task_id, FILES_ATTACHED_TO_TASK),
        task_id=task_id, files_ids=files_ids, files_names=files_names
    )
    task_response: dict = await task_service.change_schema_response(new_task, user, executor)
    task_response["extra_files"]: list[str] = files_names
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
    file_service: FileService = Depends(),
) -> TaskResponse:
    """Прикрепление файлов к задаче (запись отношения в БД) (только админ)."""
    await task_service.set_files_to_task(task_id, files_ids)
    files_names: Sequence[str] = await file_service.get_names_by_file_ids(files_ids)
    await log.ainfo(
        "{}{}{}".format(TASK, task_id, FILES_ATTACHED_TO_TASK),
        task_id=task_id, files_ids=files_ids, files_names=files_names
    )
    task: Task = await task_service.get(task_id)
    return TaskResponse(**task.__dict__, extra_files=files_names)


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
    to_unlink_files: bool = Query(None, alias=FILES_UNLINK),
    task_service: TaskService = Depends(),
    users_service: UsersService = Depends(),
    file_service: FileService = Depends(),
    user: User = Depends(current_user),
) -> AnalyticTaskResponse:
    """Редактирование задачи с возможностью очистки прикрепленных файлов, или добавления нового файла."""
    task_from_db = await task_service.get(task_id)  # get obj from db and fill in changed fields
    # get in datetime-format from db -> make it in str -> write in db in datetime again: for equal formats of datetime
    deadline: date = (
        datetime.strptime(str(deadline), DATE_FORMAT)
        if deadline is not None
        else datetime.strptime(task_from_db.deadline.strftime(DATE_FORMAT), DATE_FORMAT)
    )
    task_start: date = datetime.strptime(task_from_db.task_start.strftime(DATE_FORMAT), DATE_FORMAT)
    await check_start_not_exceeds_finish(task_start, deadline, DATE_FORMAT)
    executor = await users_service.get_by_email(executor_email.value) if executor_email is not None else None
    task_object = {
        "task_start": task_start,
        "deadline": deadline,
        "task": task_from_db.task if task is None else task,
        "tech_process": str(task_from_db.tech_process) if tech_process is None else tech_process,
        "description": task_from_db.description if description is None else description,
        "executor_id": task_from_db.executor_id if executor_email is None else executor.id,  # noqa
        "is_archived": task_from_db.is_archived if is_archived is None else is_archived
    }
    edited_task: Task = await task_service.actualize_object(task_id, TaskCreate(**task_object), user)
    edited_task_response: Sequence[dict] = await task_service.perform_changed_schema(edited_task)
    await check_not_download_and_delete_files_at_one_time(to_unlink_files, file_to_upload)
    if to_unlink_files:
        file_names_and_ids_set_to_task: tuple[list[str], list[PositiveInt]] = (
            await task_service.get_file_names_and_ids_from_task(task_id)
        )
        await task_service.set_files_to_task(task_id, [])
        edited_task_response[0]["extra_files"]: list[str] = []
        if file_names_and_ids_set_to_task[1]:
            all_file_ids_attached: list[int] = await file_service.get_all_file_ids_from_all_models()
            file_ids_unused: Sequence[int] = await file_service.get_arrays_difference(
                file_names_and_ids_set_to_task[1], all_file_ids_attached
            )
            await file_service.remove_files(file_ids_unused, FILES_DIR)
            await log.ainfo(
                "{}{}{}{}".format(TASK, task_id, SPACE, FILES_UNUSED_IN_FOLDER_REMOVED),
                task_id=task_id,
                files=file_ids_unused,
            )
        await log.ainfo(
            "{}{}".format(TASK_PATCH_FORM, task_id),
            task_id=task_id, task=task, task_description=description, is_archived=is_archived, deadline=deadline,
            tech_process=tech_process, executor=executor_email, files=None,
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
        edited_task_response[0]["extra_files"]: list[str] = new_file_names  # add dictionary for AnalyticTaskResponse
        await log.ainfo(
            "{}{}".format(TASK_PATCH_FORM, task_id),
            task_id=task_id, task=task, task_description=description, is_archived=is_archived, deadline=deadline,
            tech_process=tech_process, executor=executor_email, new_file_id=new_file_id, new_file_name=new_file_name,
            files_ids=new_file_ids, files_names=new_file_names
        )
        return AnalyticTaskResponse(**edited_task_response[0])
    await log.ainfo(
        "{}{}".format(TASK_PATCH_FORM, task_id),
        task_id=task_id, task=task, task_description=description, is_archived=is_archived, deadline=deadline,
        tech_process=tech_process, executor=executor_email
    )
    return AnalyticTaskResponse(**edited_task_response[0])


@task_router.get(
    MAIN_ROUTE,
    response_model_exclude_none=True,
    description=TASK_LIST,
    summary=TASK_LIST,
    tags=[TASKS_GET]
)
async def get_all_tasks(task_service: TaskService = Depends()) -> Sequence[AnalyticTaskResponse]:
    """Возвращает из БД все задачи: исполненные и открытые для всех пользователей."""
    return await task_service.perform_changed_schema(await task_service.get_all())  # noqa


@task_router.get(
    GET_OPENED_ROUTE,
    response_model_exclude_none=True,
    description=TASK_OPENED_LIST,
    summary=TASK_OPENED_LIST,
    tags=[TASKS_GET]
)
async def get_all_opened_tasks(task_service: TaskService = Depends()) -> Sequence[AnalyticTaskResponse]:
    """Возвращает из БД все невыполненные задачи для всех пользователей."""
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
    """Возвращает все неисполненные задачи, выставленные текущим пользователем."""
    return await task_service.perform_changed_schema(await task_service.get_tasks_ordered(user.id), user)  # noqa


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
    """Возвращает все неисполненные задачи, выставленные текущему пользователю."""
    return await task_service.perform_changed_schema(await task_service.get_my_tasks_todo(user.id), user)  # noqa


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
    """Возвращает из БД задачу по id c возможностью загрузки прикрепленных к ней файлов."""
    file_ids: Sequence[PositiveInt] = await task_service.get_file_ids_from_task(task_id)
    files_download_true = settings.CHOICE_DOWNLOAD_FILES.split('"')[-2]  # защита на случай изменений в enum-классе
    if choice_download_files == files_download_true:
        await check_exist_files_attached(file_ids, task_id)
        return await file_service.zip_files(await file_service.prepare_files_to_work_with(file_ids, FILES_DIR))
    else:
        task: Sequence[dict] = await task_service.perform_changed_schema(await task_service.get(task_id))
        return AnalyticTaskResponse(**task[0])


@task_router.delete(
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
) -> TaskDeletedResponse:
    """Удаляет по id задачу и все прикрепленные к ней файлы (из БД и каталога)."""
    task_to_delete: Task = await task_service.get(task_id)
    task_to_delete_response = task_to_delete.__dict__
    task_to_delete_response["extra_files"] = []
    files_ids_set_to_task: Sequence[int] = await task_service.get_file_ids_from_task(task_id)
    if files_ids_set_to_task:
        files_to_delete: Sequence[Path] = await file_service.prepare_files_to_work_with(
            files_ids_set_to_task, FILES_DIR
        )
        await task_service.set_files_to_task(task_id, [])
        await log.ainfo("{}{}{}{}".format(TASK, task_id, FILES_ATTACHED_TO_TASK, []), task_id=task_id, files=[])
        try:  # if files are attached to another models, they won't be deleted!!!
            await file_service.remove_files(files_ids_set_to_task, FILES_DIR)
            await log.ainfo(
                "{}{}{}{}".format(TASK, task_id, SPACE, FILES_UNUSED_IN_FOLDER_REMOVED),
                task_id=task_id,
                files=files_to_delete,
            )
        except Exception as e:  # todo кастомизировать и идентифицировать Exception
            await log.ainfo(
                "{}{}{}{}{}".format(TASK, task_id, SPACE, FILES_IDS_INTERSECTION, files_ids_set_to_task),
                exception=e,
                task_id=task_id,
                files=files_to_delete,
                intersection=files_ids_set_to_task,
            )
            await task_service.remove(task_id)
            await log.ainfo("{}{}{}".format(TASK, task_id, DELETED_OK))
            task_to_delete_response["extra_files"] = files_to_delete
            return TaskDeletedResponse(task_deleted=[task_to_delete_response], files_ids=files_ids_set_to_task)
        task_to_delete_response["extra_files"] = files_to_delete
    await task_service.remove(task_id)
    await log.ainfo("{}{}{}".format(TASK, task_id, DELETED_OK))
    return TaskDeletedResponse(task_deleted=[task_to_delete_response], files_ids=files_ids_set_to_task)
