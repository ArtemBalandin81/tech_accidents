"""src/api/endpoints/files_attached.py"""

from pathlib import Path

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from fastapi.responses import FileResponse
from src.api.constants import *
from src.api.schema import FileAttachedResponse, FileUploadedResponse  # todo subst to "schemas" after refactoring
from src.api.services import FileService
from src.core.db.models import User
from src.core.db.user import current_superuser, current_user
from src.core.enums import ChoiceDownloadFiles
from src.settings import settings

log = structlog.get_logger()
file_router = APIRouter()

SERVICES_DIR = Path(__file__).resolve().parent.parent.parent.parent
FILES_DIR = SERVICES_DIR.joinpath(settings.FILES_DOWNLOAD_DIR)

# todo проверить схемы ответа в схемах апи 200, 401, 404 и т.п.
@file_router.post(
    DOWNLOAD_FILES,
    description=UPLOAD_FILES_BY_FORM,
    summary=UPLOAD_FILES_BY_FORM,
    tags=[FILES]
)
async def upload_files_by_form(
    *,
    files_to_upload: list[UploadFile] = File(...),
    file_service: FileService = Depends(),
    user: User = Depends(current_user),  # todo убрать, ну нужен и из сервисов тоже
) -> FileUploadedResponse:
    file_timestamp = (datetime.now(TZINFO)).strftime(FILE_DATETIME_FORMAT)  # for equal file_name in db & upload folder
    download_file_names = await file_service.download_files(files_to_upload, FILES_DIR, file_timestamp)
    file_names_written_in_db = await file_service.write_files_in_db(
        download_file_names, files_to_upload, user, file_timestamp
    )
    if download_file_names != file_names_written_in_db:
        await log.aerror("{}{}{}".format(FILES_DOWNLOAD_ERROR, download_file_names, file_names_written_in_db))
        raise HTTPException(
            status_code=409,
            detail="{}{}{}".format(FILES_DOWNLOAD_ERROR, download_file_names, file_names_written_in_db)
        )
    return FileUploadedResponse(
        download_file_names=download_file_names,
        file_names_written_in_db=file_names_written_in_db,
    )


@file_router.get(
    GET_FILES,
    description=GET_SEVERAL_FILES,
    summary=GET_SEVERAL_FILES,
    tags=[FILES],
)
async def get_files(
        search_name: str = Query(None, example=SOME_NAME, alias=SEARCH_FILES_BY_NAME),
        files_wanted: list[int] = Query(None, alias=SEARCH_FILES_BY_ID),
        file_service: FileService = Depends(),
) -> Response:
    await log.ainfo("{}{}".format("search_name: ", search_name))
    await log.ainfo("{}{}".format("files_wanted: ", files_wanted))
    files_to_zip = []
    if (search_name is not None and search_name != SOME_NAME) and files_wanted is not None:
        await log.aerror(FILE_SEARCH_DOWNLOAD_OPTION)
        raise HTTPException(  # для удобства SOME_NAME допустимо в поиске по id
            status_code=403,
            detail="{}".format(FILE_SEARCH_DOWNLOAD_OPTION)
        )
    if files_wanted is not None:
        for file_id in files_wanted:
            file_db = await file_service.get(file_id)
            files_to_zip.append(FILES_DIR.joinpath(file_db.name))
    else:
        files_db = await file_service.get_all_for_search_word(search_name)  # noqa
        await log.ainfo("{}{}".format("files_received: ", files_db))
        if len(files_db) == 0:
            await log.aerror(NOT_FOUND)
            raise HTTPException(
                status_code=403,
                detail="{}".format(NOT_FOUND)
            )
        for searched_result in files_db:
            files_to_zip.append(FILES_DIR.joinpath(searched_result.name))
    return await file_service.zip_files(files_to_zip)


@file_router.get(
    FILE_ID,
    response_model=FileAttachedResponse,
    description=GET_FILE_BY_ID,
    summary=GET_FILE_BY_ID,
    tags=[FILES],
)
async def get_file_by_id(
        file_id: int,
        choice_download_files: ChoiceDownloadFiles = Query(..., alias=CHOICE_FORMAT),
        file_service: FileService = Depends(),
):
    file_db = await file_service.get(file_id)
    file_name = file_db.name
    content = f"attachment; filename={file_name}"
    headers = {"Content-Disposition": content}
    response = FileResponse(
        FILES_DIR.joinpath(file_db.name),
        headers=headers,
    )
    files_download_true = settings.CHOICE_DOWNLOAD_FILES.split('"')[-2]  # защита на случай изменений в enum-классе
    if choice_download_files == files_download_true:  # сочетает в ответе и FileResponse и схему пайдентик
        return response
    else:
        return FileAttachedResponse(
            file_info=file_db,
            files_attached=file_name
        )
