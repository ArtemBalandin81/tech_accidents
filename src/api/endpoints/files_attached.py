"""src/api/endpoints/files_attached.py"""

from pathlib import Path
from typing import Sequence

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from fastapi.responses import FileResponse
from pydantic import PositiveInt

from src.api.constants import *
from src.api.schema import FileAttachedResponse, FileUploadedResponse  # todo subst to "schemas" after refactoring
from src.api.services import FileService
from src.core.db.models import FileAttached
from src.core.db.user import current_superuser, current_user
from src.core.enums import ChoiceDownloadFiles, ChoiceRemoveFilesUnused
from src.settings import settings

log = structlog.get_logger()
file_router = APIRouter()

SERVICES_DIR = Path(__file__).resolve().parent.parent.parent.parent
FILES_DIR = SERVICES_DIR.joinpath(settings.FILES_DOWNLOAD_DIR)

async def file_uploader(files: list[UploadFile]):
    """Эксперементальная функция для испльзования в Depends() в async def upload_files_by_form."""
    await log.ainfo("{}{}".format(UPLOAD_FILES_BY_FORM, files))
    return files

# todo проверить наличие схем ответа в схемах апи 200, 401, 404 и т.п.
@file_router.post(
    DOWNLOAD_FILES,
    description=UPLOAD_FILES_BY_FORM,
    dependencies=[Depends(current_superuser)],
    summary=UPLOAD_FILES_BY_FORM,
    tags=[FILES]
)
async def upload_files_by_form(
    *,
    files_to_upload: list[UploadFile] = Depends(file_uploader),  # эксперементально
    file_service: FileService = Depends(),
) -> FileUploadedResponse:
    """Загружает файлы в каталог и записывает их в БД."""
    file_timestamp = (datetime.now(TZINFO)).strftime(FILE_DATETIME_FORMAT)  # for equal file_name in db & upload folder
    file_names_and_ids_written_in_db = await file_service.download_and_write_files_in_db(
        files_to_upload, FILES_DIR, file_timestamp
    )
    file_names_in_db = file_names_and_ids_written_in_db[0]
    file_ids_in_db = file_names_and_ids_written_in_db[1]
    return FileUploadedResponse(
        file_names_written_in_db=file_names_in_db,
        file_ids_written_in_db=file_ids_in_db
    )

@file_router.get(
    GET_FILES,
    description=GET_SEVERAL_FILES,
    dependencies=[Depends(current_user)],
    summary=GET_SEVERAL_FILES,
    tags=[FILES],
)
async def get_files(
        search_name: str = Query(None, example=SOME_NAME, alias=SEARCH_FILES_BY_NAME),
        files_ids_wanted: list[PositiveInt] = Query(None, alias=SEARCH_FILES_BY_ID),
        file_service: FileService = Depends(),
) -> Response:
    """Отдает запрашиваемые файлы по их ids, или через форму поиска в формате zip ."""
    await log.ainfo("{}{}".format(SEARCH_FILES_BY_NAME, search_name))
    await log.ainfo("{}{}".format(SEARCH_FILES_BY_ID, files_ids_wanted))
    if (search_name is not None and search_name != SOME_NAME) and files_ids_wanted is not None:
        await log.aerror(FILE_SEARCH_DOWNLOAD_OPTION)  # SOME_NAME допустимо в поиске по id
        raise HTTPException(
            status_code=403,
            detail="{}".format(FILE_SEARCH_DOWNLOAD_OPTION)
        )
    if files_ids_wanted is not None:
        files_to_zip = await file_service.prepare_files_to_work_with(files_ids_wanted, FILES_DIR)
    else:
        files_db = await file_service.get_all_for_search_word(search_name)  # noqa
        await log.ainfo("{}{}".format(FILES_RECEIVED, files_db))
        if len(files_db) == 0:
            await log.aerror(NOT_FOUND)
            raise HTTPException(status_code=403, detail="{}".format(NOT_FOUND))
        files_to_zip = [FILES_DIR.joinpath(searched_result.name) for searched_result in files_db]
    return await file_service.zip_files(files_to_zip)

# todo сервис поиска файлов, которых нет в БД, но есть в каталоге с опциональной возможностью их очистки через баттон
# todo проработать 4 сценария: бесхозные в каталоге, бесхозные в БД, удалить все бесхозные в каталоге, удалить бх в БД
@file_router.get(
    GET_FILES_UNUSED,
    description=GET_SEVERAL_FILES_UNUSED,
    dependencies=[Depends(current_superuser)],
    summary=GET_SEVERAL_FILES_UNUSED,
    tags=[FILES],
)
async def get_files_unused(
        choice_remove_files_unused: ChoiceRemoveFilesUnused = Query(..., alias=CHOICE_FORMAT),
        file_service: FileService = Depends(),
):
    """Ищет все бесхозные файлы и дает возможность их удалить из директории с файлами."""
    files_ids_db: Sequence[FileAttached] = await file_service.get_all()

    return files_ids_db  # todo


@file_router.get(
    FILE_ID,
    response_model=FileAttachedResponse,
    dependencies=[Depends(current_user)],
    description=GET_FILE_BY_ID,
    summary=GET_FILE_BY_ID,
    tags=[FILES],
)
async def get_file_by_id(
        file_id: PositiveInt,
        choice_download_files: ChoiceDownloadFiles = Query(..., alias=CHOICE_FORMAT),
        file_service: FileService = Depends(),
):
    """Ищет файл по id и либо отдает информацию о нем в json, или позволяет выгрузить файл."""
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
            files_attached=file_name,
        )

@file_router.delete(
    FILE_ID,
    description=FILE_DELETE,
    dependencies=[Depends(current_superuser)],
    summary=FILE_DELETE,
    tags=[FILES],
)
async def remove_files_from_db_and_folder(
        search_name: str = Query(None, example=SOME_NAME, alias=SEARCH_FILES_BY_NAME),
        file_ids_wanted: list[PositiveInt] = Query(None, alias=SEARCH_FILES_BY_ID),
        file_service: FileService = Depends(),
) -> Sequence[Path] | None:
    """Ищет файлы в БД по id и удаляет их из БД и каталога."""
    await log.ainfo("{}{}".format(SEARCH_FILES_BY_NAME, search_name))
    await log.ainfo("{}{}".format(SEARCH_FILES_BY_ID, file_ids_wanted))
    if (search_name is not None and search_name != SOME_NAME) and file_ids_wanted is not None:
        await log.aerror(FILE_SEARCH_DOWNLOAD_OPTION)  # SOME_NAME допустимо в поиске по id
        raise HTTPException(status_code=403, detail="{}".format(FILE_SEARCH_DOWNLOAD_OPTION))
    if file_ids_wanted is not None:
        files_to_remove = await file_service.remove_files(file_ids_wanted, FILES_DIR)
        await log.ainfo("{}{}".format(files_to_remove, DELETED_OK))
        return files_to_remove
    else:
        files_db: Sequence[FileAttached] = await file_service.get_all_for_search_word(search_name) # noqa
        await log.ainfo("{}{}".format(FILES_RECEIVED, files_db))
        if len(files_db) == 0:
            await log.aerror(NOT_FOUND)
            raise HTTPException(status_code=403, detail="{}".format(NOT_FOUND))
        files_to_remove = await file_service.remove_files([found_files.id for found_files in files_db], FILES_DIR)
        await log.ainfo("{}{}".format(files_to_remove, DELETED_OK))
        return files_to_remove
