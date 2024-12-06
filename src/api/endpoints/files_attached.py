"""src/api/endpoints/files_attached.py"""

from pathlib import Path
from typing import Sequence

import structlog
from fastapi import (APIRouter, Depends, HTTPException, Query, Response,
                     UploadFile, status)
from fastapi.responses import FileResponse
from pydantic import PositiveInt
from src.api.constants import *
from src.api.schema import (FileBase, FileDBUnusedDeletedResponse,
                            FileDBUnusedResponse, FileUnusedDeletedResponse,
                            FileUnusedResponse, FileUploadedResponse)
from src.api.services import FileService
from src.api.validators import check_same_files_not_to_download
from src.core.db.models import FileAttached
from src.core.db.user import current_superuser, current_user
from src.core.enums import ChoiceDownloadFiles, ChoiceRemoveFilesUnused
from src.settings import settings

log = structlog.get_logger()
file_router = APIRouter()

SERVICES_DIR = Path(__file__).resolve().parent.parent.parent.parent  # move to settings todo
FILES_DIR = SERVICES_DIR.joinpath(settings.FILES_DOWNLOAD_DIR)  # move to settings todo


async def file_uploader(files: list[UploadFile]):
    """Эксперементальная функция для испльзования в async def upload_files_by_form в Depends() ."""
    await log.ainfo("{}{}".format(UPLOAD_FILES_BY_FORM, files))
    return files


@file_router.post(
    DOWNLOAD_FILES,
    description=UPLOAD_FILES_BY_FORM,
    dependencies=[Depends(current_superuser)],
    summary=UPLOAD_FILES_BY_FORM,
    tags=[FILES],
    responses={
        status.HTTP_401_UNAUTHORIZED: INACTIVE_USER_WARNING,
        status.HTTP_403_FORBIDDEN: NOT_SUPER_USER_WARNING,
    },
)
async def upload_files_by_form(
    *,
    files_to_upload: list[UploadFile] = Depends(file_uploader),  # tried to make list[UploadFile] optional
    file_service: FileService = Depends(),
) -> FileUploadedResponse:
    """Загружает файлы в каталог и записывает их в БД."""
    await check_same_files_not_to_download(files_to_upload)
    file_timestamp = (datetime.now(TZINFO)).strftime(FILE_DATETIME_FORMAT)  # for equal file_name in db & upload folder
    file_names_and_ids_written_in_db = await file_service.download_and_write_files_in_db(
        files_to_upload, FILES_DIR, file_timestamp
    )
    file_ids_in_db = file_names_and_ids_written_in_db[1]
    files_uploaded: Sequence[FileAttached] = await file_service.get_by_ids(file_ids_in_db)
    return FileUploadedResponse(files_written_in_db=files_uploaded)


@file_router.get(
    GET_FILES,
    description=GET_SEVERAL_FILES,
    dependencies=[Depends(current_user)],
    summary=GET_SEVERAL_FILES,
    tags=[FILES],
    responses={
        status.HTTP_401_UNAUTHORIZED: INACTIVE_USER_WARNING,
    },
)
async def get_files(
        search_name: str = Query(None, example=SOME_NAME, alias=SEARCH_FILES_BY_NAME),
        files_ids_wanted: list[PositiveInt] = Query(None, alias=SEARCH_FILES_BY_ID),
        file_service: FileService = Depends(),
) -> Response:
    """Отдает запрашиваемые файлы по их ids, или через форму поиска в формате zip."""
    await log.ainfo("{}{}".format(SEARCH_FILES_BY_NAME, search_name))
    await log.ainfo("{}{}".format(SEARCH_FILES_BY_ID, files_ids_wanted))
    if (search_name is not None and search_name != SOME_NAME) and files_ids_wanted is not None:
        await log.aerror(FILE_SEARCH_DOWNLOAD_OPTION)  # SOME_NAME is available searching by id
        raise HTTPException(status_code=403, detail="{}".format(FILE_SEARCH_DOWNLOAD_OPTION))
    if files_ids_wanted is not None:
        files_to_zip = await file_service.prepare_files_to_work_with(files_ids_wanted, FILES_DIR)
    else:
        files_db: Sequence[FileAttached] = await file_service.get_all_for_search_word(search_name)  # noqa
        await log.ainfo("{}{}".format(FILES_RECEIVED, files_db))
        if not files_db:  # if files_db is None - download empty zip-folder instead of raising exception
            await log.aerror("{}{}{}".format(SEARCH_FILES_BY_NAME, search_name, NOT_FOUND))
            raise HTTPException(status_code=404, detail="{}{}{}".format(SEARCH_FILES_BY_NAME, search_name, NOT_FOUND))
        files_to_zip = [FILES_DIR.joinpath(searched_result.name) for searched_result in files_db]
    return await file_service.zip_files(files_to_zip)


@file_router.get(
    FILE_ID,
    response_model=FileBase,
    dependencies=[Depends(current_user)],
    description=GET_FILE_BY_ID,
    summary=GET_FILE_BY_ID,
    tags=[FILES],
    responses={
        status.HTTP_401_UNAUTHORIZED: INACTIVE_USER_WARNING,
    },
)
async def get_file_by_id(
        file_id: PositiveInt,
        choice_download_files: ChoiceDownloadFiles = Query(..., alias=CHOICE_FORMAT),
        file_service: FileService = Depends(),
):
    """Ищет файл по id и отдает информацию о нем в json, или позволяет выгрузить сам файл."""
    file_db: FileAttached = await file_service.get(file_id)
    file_name = file_db.name
    content = f"attachment; filename={file_name}"
    headers = {"Content-Disposition": content}
    response = FileResponse(FILES_DIR.joinpath(file_db.name), headers=headers)
    files_download_true = settings.CHOICE_DOWNLOAD_FILES.split('"')[-2]  # защита на случай изменений в enum-классе
    if choice_download_files == files_download_true:
        return response
    return file_db


@file_router.delete(
    GET_FILES_UNUSED,
    description=MANAGE_FILES_UNUSED,
    dependencies=[Depends(current_superuser)],
    summary=MANAGE_FILES_UNUSED,
    tags=[FILES],
    responses={
        status.HTTP_401_UNAUTHORIZED: INACTIVE_USER_WARNING,
        status.HTTP_403_FORBIDDEN: NOT_SUPER_USER_WARNING,
    },
)
async def get_files_unused(
        choices_with_files_unused: ChoiceRemoveFilesUnused = Query(..., alias=CHOICE_FORMAT),
        file_service: FileService = Depends(),
) -> FileDBUnusedResponse | FileDBUnusedDeletedResponse | FileUnusedResponse | FileUnusedDeletedResponse:
    """
    Сценарии обработки бесхозных файлов в БД и каталоге (просмотр и удаление):
    "DB_UNUSED": "unused_in_db",
    "DB_UNUSED_REMOVE": "remove_unused_in_db",
    "FOLDER_UNUSED": "unused_in_folder",
    "FOLDER_UNUSED_REMOVE": "remove_unused_in_folder"
    """
    await log.ainfo("{}{}".format(CHOICE_FORMAT, choices_with_files_unused))
    options_for_files_unused = settings.CHOICE_REMOVE_FILES_UNUSED.split('"')
    file_names_and_ids_in_db: tuple[list[str], list[int]] = await file_service.get_all_db_file_names_and_ids()
    if choices_with_files_unused == options_for_files_unused[3]:  # == "unused_in_db"
        all_file_ids_attached: list[int] = await file_service.get_all_file_ids_from_all_models()
        file_ids_unused: Sequence[int] = await file_service.get_arrays_difference(
            file_names_and_ids_in_db[1], all_file_ids_attached
        )
        files_unused: Sequence[FileAttached] = await file_service.get_by_ids(file_ids_unused)
        await log.ainfo("{}{}".format(FILES_UNUSED_IN_DB, files_unused))
        return FileDBUnusedResponse(files_unused_in_db=files_unused)
    elif choices_with_files_unused == options_for_files_unused[7]:  # == "remove_unused_in_db"
        all_file_ids_attached: list[int] = await file_service.get_all_file_ids_from_all_models()
        file_ids_unused: Sequence[int] = await file_service.get_arrays_difference(
            file_names_and_ids_in_db[1], all_file_ids_attached
        )
        files_unused: Sequence[FileAttached] = await file_service.get_by_ids(file_ids_unused)
        if not files_unused:
            await log.aerror("{}{}{}".format(FILES_IDS_UNUSED_IN_DB, files_unused, NOT_FOUND))
            raise HTTPException(
                status_code=404, detail="{}{}{}".format(FILES_IDS_UNUSED_IN_DB, files_unused, NOT_FOUND)
            )
        await file_service.remove_files(file_ids_unused, FILES_DIR)
        await log.ainfo("{}{}".format(FILES_UNUSED_IN_DB_REMOVED, files_unused))
        return FileDBUnusedDeletedResponse(file_unused_in_db_removed=files_unused)
    elif choices_with_files_unused == options_for_files_unused[11]:  # == "unused_in_folder"
        all_files_in_folder: Sequence[str] = await file_service.get_all_files_names_in_folder(FILES_DIR)
        files_unused_in_folder: Sequence[str] = await file_service.get_arrays_difference(
            all_files_in_folder, file_names_and_ids_in_db[0],
        )
        await log.ainfo("{}{}".format(FILES_UNUSED_IN_FOLDER, files_unused_in_folder))
        return FileUnusedResponse(files_unused=files_unused_in_folder,)
    elif choices_with_files_unused == options_for_files_unused[15]:  # == "remove_unused_in_folder"
        all_files_in_folder: Sequence[str] = await file_service.get_all_files_names_in_folder(FILES_DIR)
        files_unused_in_folder: Sequence[str] = await file_service.get_arrays_difference(
            all_files_in_folder, file_names_and_ids_in_db[0],
        )
        if not files_unused_in_folder:
            await log.aerror("{}{}{}".format(FILES_UNUSED_IN_FOLDER, files_unused_in_folder, NOT_FOUND))
            raise HTTPException(
                status_code=404, detail="{}{}{}".format(FILES_UNUSED_IN_FOLDER, files_unused_in_folder, NOT_FOUND)
            )
        files_to_delete: list[Path] = await file_service.prepare_files_to_work_with(files_unused_in_folder, FILES_DIR)
        await file_service.delete_files_in_folder(files_to_delete)
        await log.ainfo("{}{}".format(FILES_UNUSED_IN_FOLDER_REMOVED, files_unused_in_folder))
        return FileUnusedDeletedResponse(files_unused=files_unused_in_folder,)


@file_router.delete(
    MAIN_ROUTE,
    description=FILE_DELETE,
    dependencies=[Depends(current_superuser)],
    summary=FILE_DELETE,
    tags=[FILES],
    responses={
        status.HTTP_401_UNAUTHORIZED: INACTIVE_USER_WARNING,
        status.HTTP_403_FORBIDDEN: NOT_SUPER_USER_WARNING,
    },
)
async def remove_files_from_db_and_folder(
        search_name: str = Query(None, example=SOME_NAME, alias=SEARCH_FILES_BY_NAME),
        file_ids_wanted: list[PositiveInt] = Query(None, alias=SEARCH_FILES_BY_ID),
        file_service: FileService = Depends(),
) -> FileDBUnusedDeletedResponse | None:
    """Ищет файлы в БД по id (или имени) и удаляет их из БД и каталога с файлами."""
    await log.ainfo("{}{}".format(SEARCH_FILES_BY_NAME, search_name))
    await log.ainfo("{}{}".format(SEARCH_FILES_BY_ID, file_ids_wanted))
    if (search_name is not None and search_name != SOME_NAME) and file_ids_wanted is not None:
        await log.aerror(FILE_SEARCH_DOWNLOAD_OPTION)  # SOME_NAME допустимо в поиске по id
        raise HTTPException(status_code=403, detail="{}".format(FILE_SEARCH_DOWNLOAD_OPTION))
    if file_ids_wanted is not None:
        files_to_remove = await file_service.get_by_ids(file_ids_wanted)
        if not files_to_remove:
            await log.aerror("{}{}{}".format(GET_FILE_BY_ID, file_ids_wanted, NOT_FOUND))
            raise HTTPException(status_code=404, detail="{}{}{}".format(GET_FILE_BY_ID, file_ids_wanted, NOT_FOUND))
        await file_service.remove_files(file_ids_wanted, FILES_DIR)
        await log.ainfo("{}{}".format(files_to_remove, DELETED_OK))
        return FileDBUnusedDeletedResponse(file_unused_in_db_removed=files_to_remove)
    else:
        searched_files_db: Sequence[FileAttached] = await file_service.get_all_for_search_word(search_name) # noqa
        await log.ainfo("{}{}".format(FILES_RECEIVED, searched_files_db))
        if not searched_files_db:
            await log.aerror("{}{}{}".format(SEARCH_FILES_BY_NAME, search_name, NOT_FOUND))
            raise HTTPException(status_code=404, detail="{}{}{}".format(SEARCH_FILES_BY_NAME, search_name, NOT_FOUND))
        await file_service.remove_files([found_files.id for found_files in searched_files_db], FILES_DIR)
        await log.ainfo("{}{}".format(searched_files_db, DELETED_OK))
        return FileDBUnusedDeletedResponse(file_unused_in_db_removed=searched_files_db)
