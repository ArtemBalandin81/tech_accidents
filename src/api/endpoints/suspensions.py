"""src/api/endpoints/suspensions.py"""

from collections.abc import Sequence
from pathlib import Path
from typing import Optional

import structlog
from fastapi import (APIRouter, Depends, File, Query, Response, UploadFile,
                     status)
from pydantic import PositiveInt
from src.api.constants import *
from src.api.schema import (AnalyticsSuspensions,
                            AnalyticSuspensionResponse, SuspensionCreate,
                            SuspensionDeletedResponse, SuspensionResponse)
from src.api.services import FileService, SuspensionService, UsersService
from src.api.validators import (
    check_author_or_super_user, check_exist_files_attached,
    check_not_download_and_delete_files_at_one_time,
    check_start_not_exceeds_finish)
from src.core.db.models import Suspension, User
from src.core.db.user import current_superuser, current_user
from src.core.enums import (ChoiceDownloadFiles, Executor, RiskAccidentSource,
                            TechProcess)

log = structlog.get_logger()
suspension_router = APIRouter()

SERVICES_DIR = Path(__file__).resolve().parent.parent.parent.parent
FILES_DIR = SERVICES_DIR.joinpath(settings.FILES_DOWNLOAD_DIR)


@suspension_router.get(
    ANALYTICS,
    response_model_exclude_none=True,
    description=ANALYTICS_SUSPENSION_LIST,
    summary=ANALYTICS_SUSPENSION_LIST,
    dependencies=[Depends(current_user)],
    tags=[ANALYTICS_SUSPENSION],
    responses={
        status.HTTP_401_UNAUTHORIZED: INACTIVE_USER_WARNING,
        status.HTTP_422_UNPROCESSABLE_ENTITY: START_FINISH_TIME,
    },
)
async def get_all_for_period_time(
    start_sample: str = Query(
        ...,
        example=ANALYTIC_FROM_TIME,
        alias=ANALYTICS_START,
        # regex=DATE_TIME_PATTERN_FORM,  # better use "check_start_not_exceeds_finish" validator
        # description=ANALYTIC_FROM_TIME,
    ),
    finish_sample: str = Query(
        ...,
        example=ANALYTIC_TO_TIME,
        alias=ANALYTICS_FINISH,
        # regex=DATE_TIME_PATTERN_FORM,  # better use "check_start_not_exceeds_finish" validator
        # description=ANALYTIC_TO_TIME,
    ),
    user: Executor = Query(None, alias=USER_MAIL),
    suspension_service: SuspensionService = Depends(),
    users_service: UsersService = Depends(),
) -> AnalyticsSuspensions:
    """Получение аналитики по простоям."""
    await check_start_not_exceeds_finish(start_sample, finish_sample, DATE_TIME_FORMAT)
    start_sample: datetime = datetime.strptime(start_sample, DATE_TIME_FORMAT)  # convert in datetime
    finish_sample: datetime = datetime.strptime(finish_sample, DATE_TIME_FORMAT)  # convert in datetime
    if user is None:
        user_id = None
    else:
        user: User = await users_service.get_by_email(user.value)
        user_id = user.id
    suspensions: Sequence[Suspension] = await suspension_service.get_suspensions_for_users(
        user_id, start_sample, finish_sample
    )
    suspensions_list = await suspension_service.perform_changed_schema(suspensions)
    return AnalyticsSuspensions(
        suspensions_in_mins_total=(
            await suspension_service.sum_suspensions_time_for_period(user_id, start_sample, finish_sample)
        ),
        suspensions_total=(
            await suspension_service.count_suspensions_for_period(user_id, start_sample, finish_sample)
        ),
        suspension_max_time_for_period=(
            await suspension_service.suspension_max_time_for_period(user_id, start_sample, finish_sample)
        ),
        last_time_suspension=await suspension_service.get_last_suspension_time(user_id),
        last_time_suspension_id=await suspension_service.get_last_suspension_id(user_id),
        suspensions_list=suspensions_list
    )


@suspension_router.post(
    POST_SUSPENSION_FORM,
    description=SUSPENSION_CREATE_FORM,
    summary=SUSPENSION_CREATE_FORM,
    tags=[SUSPENSIONS_POST],
    responses={
        status.HTTP_401_UNAUTHORIZED: INACTIVE_USER_WARNING,
        status.HTTP_422_UNPROCESSABLE_ENTITY: START_FINISH_TIME,
    },
)
async def create_new_suspension_by_form(
    *,
    file_to_upload: UploadFile = None,
    suspension_start: str = Query(
        ...,
        example=CREATE_SUSPENSION_FROM_TIME,
        alias=ANALYTICS_START,
        # regex=DATE_TIME_PATTERN_FORM,  # better use "check_start_not_exceeds_finish" validator
        # description=CREATE_SUSPENSION_FROM_TIME,
    ),
    suspension_finish: str = Query(
        ...,
        example=CREATE_SUSPENSION_TO_TIME,
        alias=ANALYTICS_FINISH,
        # regex=DATE_TIME_PATTERN_FORM,  # better use "check_start_not_exceeds_finish" validator
        # description=CREATE_SUSPENSION_TO_TIME,
    ),
    risk_accident: RiskAccidentSource = Query(..., alias=RISK_ACCIDENT_SOURCE),
    tech_process: TechProcess = Query(..., alias=TECH_PROCESS),
    description: str = Query(..., max_length=256, example=CREATE_DESCRIPTION, alias=SUSPENSION_DESCRIPTION),
    implementing_measures: str = Query(..., max_length=256, example=MEASURES, alias=IMPLEMENTING_MEASURES),
    file_service: FileService = Depends(),
    suspension_service: SuspensionService = Depends(),
    user: User = Depends(current_user),
) -> AnalyticSuspensionResponse:
    """Фиксация случая простоя из формы с возможностью загрузки 1 файла."""
    await check_start_not_exceeds_finish(suspension_start, suspension_finish, DATE_TIME_FORMAT)
    suspension_object = {
        "suspension_start": datetime.strptime(suspension_start, DATE_TIME_FORMAT),  # reverse in datetime
        "suspension_finish": datetime.strptime(suspension_finish, DATE_TIME_FORMAT),  # reverse in datetime
        "risk_accident": risk_accident.value,
        "tech_process": tech_process.value,
        "description": description,
        "implementing_measures": implementing_measures,
    }
    new_suspension: Suspension = await suspension_service.actualize_object(
        None, SuspensionCreate(**suspension_object), user
    )
    suspension_response: dict = await suspension_service.change_schema_response(new_suspension, user)
    if file_to_upload is None:
        return AnalyticSuspensionResponse(**suspension_response)
    # 2. Download and write files in db and make records in tables "files" & "suspensions_files" in db:
    file_timestamp = (datetime.now(TZINFO)).strftime(FILE_DATETIME_FORMAT)  # timestamp in filename
    file_names_and_ids: tuple[list[str], list[PositiveInt]] = await file_service.download_and_write_files_in_db(
        [file_to_upload], FILES_DIR, file_timestamp
    )
    suspension_id = new_suspension.id
    file_id = file_names_and_ids[1]
    file_name = file_names_and_ids[0]
    await suspension_service.set_files_to_suspension(suspension_id, file_id)
    await log.ainfo("{}".format(
        FILES_ATTACHED_TO_SUSPENSION), suspension_id=suspension_id, file_id=file_id, file_name=file_name
    )
    suspension_response["extra_files"]: list[str] = file_name  # add dictionary for AnalyticSuspensionResponse
    return AnalyticSuspensionResponse(**suspension_response)


@suspension_router.post(
    POST_SUSPENSION_FILES_FORM,
    description=SUSPENSION_FILES_CREATE_FORM,
    summary=SUSPENSION_FILES_CREATE_FORM,
    tags=[SUSPENSIONS_POST],
    responses={
        status.HTTP_401_UNAUTHORIZED: INACTIVE_USER_WARNING,
        status.HTTP_422_UNPROCESSABLE_ENTITY: START_FINISH_TIME,
    },
)
async def create_new_suspension_by_form_with_files(
    *,
    files_to_upload: list[UploadFile] = File(...),
    suspension_start: str = Query(
        ...,
        example=CREATE_SUSPENSION_FROM_TIME,
        alias=ANALYTICS_START,
        # regex=DATE_TIME_PATTERN_FORM,  # better use "check_start_not_exceeds_finish" validator
        # description=CREATE_SUSPENSION_FROM_TIME,
    ),
    suspension_finish: str = Query(
        ...,
        example=CREATE_SUSPENSION_TO_TIME,
        alias=ANALYTICS_FINISH,
        # regex=DATE_TIME_PATTERN_FORM,  # better use "check_start_not_exceeds_finish" validator
        # description=CREATE_SUSPENSION_TO_TIME,
    ),
    risk_accident: RiskAccidentSource = Query(..., alias=RISK_ACCIDENT_SOURCE),
    tech_process: TechProcess = Query(..., alias=TECH_PROCESS),
    description: str = Query(..., max_length=256, example=CREATE_DESCRIPTION, alias=SUSPENSION_DESCRIPTION),
    implementing_measures: str = Query(..., max_length=256, example=MEASURES, alias=IMPLEMENTING_MEASURES),
    file_service: FileService = Depends(),
    suspension_service: SuspensionService = Depends(),
    user: User = Depends(current_user),
) -> AnalyticSuspensionResponse:
    """Фиксация случая простоя из формы с обязательной загрузкой нескольких файлов."""
    await check_start_not_exceeds_finish(suspension_start, suspension_finish, DATE_TIME_FORMAT)
    suspension_object = {
        "suspension_start": datetime.strptime(suspension_start, DATE_TIME_FORMAT),  # reverse in datetime
        "suspension_finish": datetime.strptime(suspension_finish, DATE_TIME_FORMAT),  # reverse in datetime
        "risk_accident": risk_accident.value,
        "tech_process": tech_process.value,
        "description": description,
        "implementing_measures": implementing_measures,
    }
    new_suspension: Suspension = await suspension_service.actualize_object(
        None, SuspensionCreate(**suspension_object), user
    )
    suspension_response: dict = await suspension_service.change_schema_response(new_suspension, user)
    # 2. Download and write files in db and make records in tables "files" & "suspensions_files" in db:
    file_timestamp = (datetime.now(TZINFO)).strftime(FILE_DATETIME_FORMAT)  # timestamp in filename
    file_names_and_ids: tuple[list[str], list[PositiveInt]] = await file_service.download_and_write_files_in_db(
        files_to_upload, FILES_DIR, file_timestamp
    )
    suspension_id = new_suspension.id
    files_ids = file_names_and_ids[1]
    files_names = file_names_and_ids[0]
    await suspension_service.set_files_to_suspension(suspension_id, files_ids)
    await log.ainfo("{}".format(
        FILES_ATTACHED_TO_SUSPENSION), suspension_id=suspension_id, files_ids=files_ids, files_names=files_names
    )
    suspension_response["extra_files"]: list[str] = files_names  # add dictionary for AnalyticSuspensionResponse
    return AnalyticSuspensionResponse(**suspension_response)


@suspension_router.post(
    ADD_FILES_TO_SUSPENSION,
    description=SET_FILES_LIST_TO_SUSPENSION,
    summary=SET_FILES_LIST_TO_SUSPENSION,
    dependencies=[Depends(current_superuser)],
    tags=[SUSPENSIONS_POST],
    responses={
        status.HTTP_401_UNAUTHORIZED: INACTIVE_USER_WARNING,
        status.HTTP_403_FORBIDDEN: NOT_SUPER_USER_WARNING,
    },
)
async def set_files_to_suspension(
    *,
    suspension_id: PositiveInt,
    files_ids: list[PositiveInt] = Query(None, alias=SET_FILES_LIST_TO_SUSPENSION),
    suspension_service: SuspensionService = Depends(),
    file_service: FileService = Depends(),
) -> SuspensionResponse:
    """Прикрепление файлов к случаям простоев (запись отношения в БД) (только админ)."""
    await suspension_service.set_files_to_suspension(suspension_id, files_ids)
    files_names: Sequence[str] = await file_service.get_names_by_file_ids(files_ids)
    await log.ainfo(
        "{}{}{}".format(SUSPENSION, suspension_id, FILES_ATTACHED_TO_SUSPENSION),
        suspension_id=suspension_id, files_ids=files_ids, files_names=files_names
    )
    suspension: Suspension = await suspension_service.get(suspension_id)
    return SuspensionResponse(**suspension.__dict__, extra_files=files_names)


@suspension_router.patch(
    SUSPENSION_ID,
    description=SUSPENSION_PATCH_FORM,
    summary=SUSPENSION_PATCH_FORM,
    tags=[SUSPENSIONS_POST],
    responses={
        status.HTTP_401_UNAUTHORIZED: INACTIVE_USER_WARNING,
        status.HTTP_422_UNPROCESSABLE_ENTITY: START_FINISH_TIME,
    },
)
async def partially_update_suspension_by_form(
    suspension_id: PositiveInt,
    suspension_start: Optional[str] = Query(
        None,
        description=CREATE_SUSPENSION_FROM_TIME,
        alias=ANALYTICS_START,
        # regex=DATE_TIME_PATTERN_FORM,  # better use "check_start_not_exceeds_finish" validator
    ),
    suspension_finish: Optional[str] = Query(
        None,
        description=CREATE_SUSPENSION_TO_TIME,
        alias=ANALYTICS_FINISH,
        # regex=DATE_TIME_PATTERN_FORM,  # better use "check_start_not_exceeds_finish" validator
    ),
    risk_accident: RiskAccidentSource = Query(None, alias=RISK_ACCIDENT_SOURCE),
    tech_process: TechProcess = Query(None, alias=TECH_PROCESS),
    description: Optional[str] = Query(None, max_length=256, alias=SUSPENSION_DESCRIPTION),
    implementing_measures: Optional[str] = Query(None, max_length=256, alias=IMPLEMENTING_MEASURES),
    file_to_upload: UploadFile = None,
    to_unlink_files: bool = Query(None, alias=FILES_UNLINK),
    file_service: FileService = Depends(),
    suspension_service: SuspensionService = Depends(),
    user: User = Depends(current_user),
) -> AnalyticSuspensionResponse:
    """Редактирование случая простоя с возможностью очистки прикрепленных файлов, или добавления нового файла."""
    await check_start_not_exceeds_finish(suspension_start, suspension_finish, DATE_TIME_FORMAT)  # из формы
    suspension_from_db = await suspension_service.get(suspension_id)  # get obj from db and fill in changed fields
    await check_author_or_super_user(user, suspension_from_db)
    # get in datetime-format from db -> make it in str -> write in db in datetime again: for equal formats of datetime
    suspension_start: datetime = (
        datetime.strptime(str(suspension_start), DATE_TIME_FORMAT)
        if suspension_start is not None
        else datetime.strptime(suspension_from_db.suspension_start.strftime(DATE_TIME_FORMAT), DATE_TIME_FORMAT)
    )
    suspension_finish: datetime = (
        datetime.strptime(str(suspension_finish), DATE_TIME_FORMAT)
        if suspension_finish is not None
        else datetime.strptime(suspension_from_db.suspension_finish.strftime(DATE_TIME_FORMAT), DATE_TIME_FORMAT)
    )
    await check_start_not_exceeds_finish(suspension_start, suspension_finish, DATE_TIME_FORMAT)  # из формы и бд
    suspension_object = {
        "suspension_start": suspension_start,
        "suspension_finish": suspension_finish,
        "risk_accident": suspension_from_db.risk_accident if risk_accident is None else risk_accident,
        "tech_process": str(suspension_from_db.tech_process) if tech_process is None else tech_process,
        "description": suspension_from_db.description if description is None else description,
        "implementing_measures": (
            suspension_from_db.implementing_measures if implementing_measures is None else implementing_measures
        ),
    }
    edited_suspension: Suspension = await suspension_service.actualize_object(
        suspension_id, SuspensionCreate(**suspension_object), user
    )
    edited_suspension_response: Sequence[dict] = await suspension_service.perform_changed_schema(edited_suspension)
    await check_not_download_and_delete_files_at_one_time(to_unlink_files, file_to_upload)
    if to_unlink_files:
        file_names_and_ids_set_to_suspension: tuple[list[str], list[PositiveInt]] = (
            await suspension_service.get_file_names_and_ids_from_suspension(suspension_id)
        )
        await suspension_service.set_files_to_suspension(suspension_id, [])
        edited_suspension_response[0]["extra_files"]: list[str] = []
        if file_names_and_ids_set_to_suspension[1]:
            all_file_ids_attached: list[int] = await file_service.get_all_file_ids_from_all_models()
            file_ids_unused: Sequence[int] = await file_service.get_arrays_difference(
                file_names_and_ids_set_to_suspension[1], all_file_ids_attached
            )
            await file_service.remove_files(file_ids_unused, FILES_DIR)
            await log.ainfo(
                "{}{}{}{}".format(SUSPENSION, suspension_id, SPACE, FILES_UNUSED_IN_FOLDER_REMOVED),
                suspension_id=suspension_id,
                files=file_ids_unused,
            )
        await log.ainfo(
            "{}{}".format(SUSPENSION_PATCH_FORM, suspension_id),
            suspension_id=suspension_id, risk_accident=risk_accident, suspension_description=description, files=None,
            suspension_start=suspension_start, suspension_finish=suspension_finish, tech_process=tech_process,
            implementing_measures=implementing_measures
        )
        return AnalyticSuspensionResponse(**edited_suspension_response[0])
    if file_to_upload is not None:  # 2. Сохраняем файл и вносим о нем записи в таблицы files и suspensions_files в БД
        file_timestamp = (datetime.now(TZINFO)).strftime(FILE_DATETIME_FORMAT)  # метка времени в имени файла
        file_names_and_ids_attached: tuple[list[str], list[PositiveInt]] = (
            await file_service.download_and_write_files_in_db(
                [file_to_upload], FILES_DIR, file_timestamp)
        )
        new_file_id = file_names_and_ids_attached[1]
        new_file_name = file_names_and_ids_attached[0]
        file_names_and_ids_set_to_suspension: tuple[list[str], list[PositiveInt]] = (
            await suspension_service.get_file_names_and_ids_from_suspension(suspension_id)
        )
        new_file_ids = new_file_id + file_names_and_ids_set_to_suspension[1]
        new_file_names = new_file_name + file_names_and_ids_set_to_suspension[0]
        await suspension_service.set_files_to_suspension(suspension_id, new_file_ids)
        edited_suspension_response[0]["extra_files"]: list[str] = new_file_names  # for AnalyticSuspensionResponse
        await log.ainfo(
            "{}{}".format(SUSPENSION_PATCH_FORM, suspension_id),
            suspension_id=suspension_id, risk_accident=risk_accident, suspension_description=description,
            suspension_start=suspension_start, suspension_finish=suspension_finish, tech_process=tech_process,
            implementing_measures=implementing_measures, new_file_id=new_file_id, new_file_name=new_file_name,
            files_ids=new_file_ids, files_names=new_file_names
        )
        return AnalyticSuspensionResponse(**edited_suspension_response[0])
    await log.ainfo(
        "{}{}".format(SUSPENSION_PATCH_FORM, suspension_id),
        suspension_id=suspension_id, risk_accident=risk_accident, suspension_description=description,
        suspension_start=suspension_start, suspension_finish=suspension_finish, tech_process=tech_process,
        implementing_measures=implementing_measures
    )
    return AnalyticSuspensionResponse(**edited_suspension_response[0])


@suspension_router.get(
    MAIN_ROUTE,
    dependencies=[Depends(current_user)],
    response_model_exclude_none=True,
    description=SUSPENSION_LIST,
    summary=SUSPENSION_LIST,
    tags=[SUSPENSIONS_GET],
    responses={
        status.HTTP_401_UNAUTHORIZED: INACTIVE_USER_WARNING,
    },
)
async def get_all_suspensions(
        suspension_service: SuspensionService = Depends()
) -> Sequence[AnalyticSuspensionResponse]:
    """Все случаи простоя."""
    return await suspension_service.perform_changed_schema(await suspension_service.get_all())  # noqa


@suspension_router.get(
    MY_SUSPENSIONS,
    response_model_exclude_none=True,
    description=SUSPENSION_LIST_CURRENT_USER,
    summary=SUSPENSION_LIST_CURRENT_USER,
    tags=[SUSPENSIONS_GET],
    responses={
        status.HTTP_401_UNAUTHORIZED: INACTIVE_USER_WARNING,
    },
)
async def get_all_my_suspensions(
    suspension_service: SuspensionService = Depends(),
    user: User = Depends(current_user)
) -> Sequence[AnalyticSuspensionResponse]:
    """Все случаи простоя, зафиксированные текущим пользователем."""
    return await suspension_service.perform_changed_schema(  # noqa
        await suspension_service.get_all_my_suspensions(user.id), user  # noqa
    )  # noqa


@suspension_router.get(
    SUSPENSION_ID,
    response_model=None,  # Invalid args for response field -> response_model=None
    dependencies=[Depends(current_user)],
    description=SUSPENSION_DESCRIPTION,
    summary=SUSPENSION_DESCRIPTION,
    tags=[SUSPENSIONS_GET],
    responses={
        status.HTTP_401_UNAUTHORIZED: INACTIVE_USER_WARNING,
    },
)
async def get_suspension_by_id(
    suspension_id: PositiveInt,
    choice_download_files: ChoiceDownloadFiles = Query(..., alias=CHOICE_FORMAT),
    suspension_service: SuspensionService = Depends(),
    file_service: FileService = Depends()
) -> AnalyticSuspensionResponse | Response:  # Invalid args for response field -> response_model=None
    """Возвращает из БД задачу по id c возможностью загрузки прикрепленных к ней файлов."""
    file_ids: Sequence[PositiveInt] = await suspension_service.get_file_ids_from_suspension(suspension_id)
    files_download_true = settings.CHOICE_DOWNLOAD_FILES.split('"')[-2]  # защита на случай изменений в enum-классе
    if choice_download_files == files_download_true:
        await check_exist_files_attached(file_ids, suspension_id)
        return await file_service.zip_files(await file_service.prepare_files_to_work_with(file_ids, FILES_DIR))
    else:
        suspension: Sequence[dict] = await suspension_service.perform_changed_schema(
            await suspension_service.get(suspension_id)
        )
        return AnalyticSuspensionResponse(**suspension[0])


@suspension_router.delete(
    SUSPENSION_ID,
    description=SUSPENSION_DELETE,
    dependencies=[Depends(current_superuser)],
    summary=SUSPENSION_DELETE,
    tags=[SUSPENSIONS_POST],
    responses={
        status.HTTP_401_UNAUTHORIZED: INACTIVE_USER_WARNING,
        status.HTTP_403_FORBIDDEN: NOT_SUPER_USER_WARNING,
    },
)
async def remove_suspension(
        suspension_id: PositiveInt,
        file_service: FileService = Depends(),
        suspension_service: SuspensionService = Depends()
) -> SuspensionDeletedResponse:
    """Удаляет по id случай простоя и все прикрепленные к нему файлы (из БД и каталога)."""
    suspension_to_delete: Suspension = await suspension_service.get(suspension_id)
    suspension_to_delete_response = suspension_to_delete.__dict__
    suspension_to_delete_response["extra_files"] = []
    files_ids_set_to_suspension: Sequence[int] = await suspension_service.get_file_ids_from_suspension(suspension_id)
    if files_ids_set_to_suspension:
        files_to_delete: Sequence[Path] = await file_service.prepare_files_to_work_with(
            files_ids_set_to_suspension, FILES_DIR
        )
        await suspension_service.set_files_to_suspension(suspension_id, [])
        await log.ainfo(
            "{}{}{}{}".format(SUSPENSION, suspension_id, FILES_ATTACHED_TO_SUSPENSION, []),
            suspension_id=suspension_id,
            files=[]
        )
        try:  # if files are attached to another models, they won't be deleted!!!
            await file_service.remove_files(files_ids_set_to_suspension, FILES_DIR)
            await log.ainfo(
                "{}{}{}{}".format(SUSPENSION, suspension_id, SPACE, FILES_UNUSED_IN_FOLDER_REMOVED),
                suspension_id=suspension_id,
                files=files_to_delete,
            )
        except Exception as e:  # todo кастомизировать и идентифицировать Exception
            await log.ainfo(
                "{}{}{}{}{}".format(
                    SUSPENSION, suspension_id, SPACE, FILES_IDS_INTERSECTION, files_ids_set_to_suspension
                ),
                exception=e,
                suspension_id=suspension_id,
                files=files_to_delete,
                intersection=files_ids_set_to_suspension,
            )
            await suspension_service.remove(suspension_id)
            await log.ainfo("{}{}{}".format(SUSPENSION, suspension_id, DELETED_OK))
            suspension_to_delete_response["extra_files"] = files_to_delete
            return SuspensionDeletedResponse(
                suspension_deleted=[suspension_to_delete_response], files_ids=files_ids_set_to_suspension
            )
        suspension_to_delete_response["extra_files"] = files_to_delete
    await suspension_service.remove(suspension_id)
    await log.ainfo("{}{}{}".format(SUSPENSION, suspension_id, DELETED_OK))
    return SuspensionDeletedResponse(
        suspension_deleted=[suspension_to_delete_response], files_ids=files_ids_set_to_suspension
    )
