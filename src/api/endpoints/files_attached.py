"""src/api/endpoints/files_attached.py"""
from collections.abc import Sequence
from datetime import date, datetime
from pathlib import Path
from typing import Optional
import os
import zipfile
import io

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import EmailStr, PositiveInt
from src.api.constants import *
from src.api.schema import FileBase, FileAttachedResponse, FileUploadedResponse  # todo subst to "schemas" after schemas refactoring
from src.api.services import FileService, TaskService, UsersService
from src.core.db.models import User
from src.core.db.user import current_superuser, current_user


log = structlog.get_logger()
file_router = APIRouter()

SERVICES_DIR = Path(__file__).resolve().parent.parent.parent.parent
FILES_DIR = SERVICES_DIR.joinpath("uploaded_files2")  # todo в settings & .env!

# todo проверить схемы ответа в схемах апи 200, 401, 404 и т.п.
@file_router.post(
    "/download_files",  # todo в константы
    description="Загрузка файлов из формы.",  # todo в константы
    summary="Загрузка файлов из формы.",  # todo в константы
    tags=["Files"]  # todo в константы
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
        raise HTTPException(
            status_code=409,
            detail="{}{}{}".format(FILES_DOWNLOAD_ERROR, download_file_names, file_names_written_in_db)
        )
    return FileUploadedResponse(
        download_file_names=download_file_names,
        file_names_written_in_db=file_names_written_in_db,
    )


@file_router.get(
    "/get_files",  # todo в константы
    # response_model= ???,  # todo
    description="Получить несколько файлов.",  # todo в константы
    summary="Получить несколько файлов.",  # todo в константы
    tags=["Files"],  # todo в константы
)
async def get_files(
        files_wanted: list[int] = Query(None, example=23, alias="Список файлов"),  # todo в константы
        file_service: FileService = Depends(),
):
    files_to_zip = []
    for file_id in files_wanted:
        file_db = await file_service.get(file_id)
        files_to_zip.append(FILES_DIR.joinpath(file_db.name))
    print((datetime.now(TZINFO)).strftime(FILE_DATETIME_FORMAT))
    return await file_service.zip_files(files_to_zip)


@file_router.get(
    "/{file_id}",  # todo в константы
    # response_model=FileBase,  # todo
    # response_model=FileAttachedResponse,
    # response_class=FileResponse,
    description="Получить файл по id.",  # todo в константы
    summary="Получить файл по id.",  # todo в константы
    tags=["Files"],  # todo в константы
)
async def get_file_by_id(
        file_id: int,
        img: bool | None = None,  # todo enum переключатель
        file_service: FileService = Depends(),
# ) -> FileAttachedResponse | FileResponse:  # todo валидировать ответ все равно как-то нужно
):
    file_db = await file_service.get(file_id)
    file_name = file_db.name
    content = f"attachment; filename={file_name}"
    headers = {"Content-Disposition": content}
    response = FileResponse(
        FILES_DIR.joinpath(file_db.name),
        headers=headers,
    )
    if img:  # сочетает в ответе и FileResponse и схему пайдентик
        return response
    else:
        return FileAttachedResponse(
            file_info=file_db,
            # file_path=FILES_DIR.joinpath(file_db.name),
            files_attached=file_name
        )
