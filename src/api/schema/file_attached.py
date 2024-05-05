"""src/api/schemas/files.py"""
import time
from datetime import date
from typing import Type

from pydantic import BaseModel, FilePath, Field, computed_field, field_serializer, StrictBytes, Base64Bytes, Base64Str
# from sqlalchemy import BLOB
from sqlalchemy.sql.sqltypes import BLOB
from fastapi.responses import FileResponse

from src.api.constants import *
from src.settings import settings


class FileBase(BaseModel):
    """Базовая схема для работы с моделью файлов."""
    id: int
    name: str = Field(
        ...,
        max_length=256,
        title="Имя файла.",
        serialization_alias="Имя файла.",
        example="Some_file_name"
    )
    created_at: datetime = Field(..., serialization_alias=CREATED)
    updated_at: datetime = Field(..., serialization_alias=UPDATED)

    @field_serializer("created_at", "updated_at")
    def serialize_server_time_to_time_shift(self, server_time: datetime, _info):
        """Отображает сохраненное время сервера с требуемым сдвигом."""
        return (server_time + timedelta(hours=settings.TIMEZONE_OFFSET)).strftime(DATE_TIME_FORMAT)

    class Config:
        """Implement a custom json serializer by using pydantic's custom json encoders.
        Переводит datetime из БД в формат str для удобства отображения."""
        json_encoders = {date: lambda db_date_time: (db_date_time + timedelta(hours=0)).strftime(DATE_FORMAT)}
        from_attributes = True  # in V2: 'orm_mode' has been renamed to 'from_attributes'


class FileAttachedResponse(BaseModel):
    """Схема ответа для модели файлов."""
    file_info: FileBase = Field(..., serialization_alias="Описание файла")
    # file_path: FilePath
    files_attached: str = Field(..., serialization_alias="Дополнительные файлы")

    class Config:
        """Implement a custom json serializer by using pydantic's custom json encoders.
        Переводит datetime из БД в формат str для удобства отображения."""
        json_encoders = {date: lambda db_date_time: (db_date_time + timedelta(hours=0)).strftime(DATE_FORMAT)}
        from_attributes = True  # in V2: 'orm_mode' has been renamed to 'from_attributes'


class FileUploadedResponse(BaseModel):
    """Схема ответа после загрузки файлов."""
    download_file_names: list[str] = Field(..., serialization_alias=FILES_UPLOADED)
    file_names_written_in_db: list[str] = Field(..., serialization_alias=FILES_WRITTEN_DB)
