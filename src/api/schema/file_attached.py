"""src/api/schemas/files.py"""
from datetime import date

from pydantic import BaseModel, FilePath, Field, computed_field, field_serializer, PositiveInt

from src.api.constants import *
from src.settings import settings


class FileBase(BaseModel):
    """Базовая схема для работы с моделью файлов."""
    id: PositiveInt
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


class FileUploadedResponse(BaseModel):
    """Схема ответа после загрузки файлов."""
    files_written_in_db: list[FileBase] = Field(..., serialization_alias=FILES_WRITTEN_DB)


class FileDBUnusedResponse(BaseModel):
    """Схема ответа для поиска бесхозных файлов в БД."""
    files_unused_in_db: list[FileBase] = Field(..., serialization_alias=FILES_UNUSED_IN_DB)


class FileDBUnusedDeletedResponse(BaseModel):
    """Схема ответа после удаления бесхозных файлов в БД."""
    file_unused_in_db_removed: list[FileBase] = Field(..., serialization_alias=FILES_UNUSED_IN_DB_REMOVED)


class FileUnusedResponse(BaseModel):
    """Схема ответа для поиска бесхозных файлов в каталоге файлов."""
    files_unused: list[str] = Field(..., serialization_alias=FILES_UNUSED_IN_FOLDER)


class FileUnusedDeletedResponse(BaseModel):
    """Схема ответа после удаления бесхозных файлов из каталога."""
    files_unused: list[str] = Field(..., serialization_alias=FILES_UNUSED_IN_FOLDER_REMOVED)
