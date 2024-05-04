"""src/api/endpoints/files_attached.py"""
from collections.abc import Sequence
from datetime import date, datetime
from pathlib import Path
from typing import Optional
import os
import zipfile
import io

import structlog
from fastapi import APIRouter, Depends, File, Query, Response, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import EmailStr, PositiveInt
from src.api.constants import *
from src.api.schema import FileBase, FileAttachedResponse  # todo subst to "schemas" after schemas refactoring
from src.api.services import FileService, TaskService, UsersService
from src.core.db.models import User
from src.core.db.user import current_superuser, current_user


log = structlog.get_logger()
file_router = APIRouter()

SERVICES_DIR = Path(__file__).resolve().parent.parent.parent.parent
FILES_DIR = SERVICES_DIR.joinpath("uploaded_files")  # todo в settings & .env!


@file_router.post(
    "/files",
    description="Загрузка файлов из формы.",
    summary="Загрузка файлов из формы.",
    tags=["Files"]
)
async def upload_new_file_by_form(
    *,
    file_attached: UploadFile = File(...),  # todo upload file
    # file_name: str = Query(..., max_length=256, example="Some_file_name", alias="Имя файла"),
    # several_files: list[UploadFile] = File(...),
    file_service: FileService = Depends(),
    users_service: UsersService = Depends(),
    user: User = Depends(current_user),
# ) -> AnalyticTaskResponse:
):
    file_name = FILE_NAME_SAVE_FORMAT + "_" + file_attached.filename  # todo переводить кирилицу в латиницу
    # file_name = file_attached.filename
    try:  # todo сделать функцию и вынести в сервис + возможность обработки нескольких файлов
        with open(FILES_DIR.joinpath(file_name), "wb") as f:
            f.write(file_attached.file.read())
    except Exception as e:
        return {"message": e.args}

    file_object = {
        "name": file_name,
        # "file": file_attached.file.read(),
        "file": bytes(file_name, 'utf-8'),
        # "file": bytes(file_attached.content_type, 'utf-8'),
    }
    new_file = await file_service.actualize_object(None, file_object, user)


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
