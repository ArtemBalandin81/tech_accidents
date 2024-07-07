"""src/api/schema/suspensions.py"""

import time
from datetime import date
from typing import Optional

from pydantic import (BaseModel, Extra, Field, PositiveInt, computed_field,
                      field_serializer)
from src.api.constants import *
from src.core.enums import RiskAccidentSource, TechProcess
from src.settings import settings


class SuspensionBaseNew(BaseModel):  # todo rename
    """Базовая схема простоев."""
    id: PositiveInt
    risk_accident: RiskAccidentSource = Field(..., serialization_alias=RISK_ACCIDENT)
    tech_process: PositiveInt = Field(..., serialization_alias=TECH_PROCESS)
    created_at: datetime = Field(..., serialization_alias=CREATED)
    updated_at: datetime = Field(..., serialization_alias=UPDATED)
    description: str = Field(
        ...,
        max_length=SUSPENSION_DESCRIPTION_LENGTH,
        title=SUSPENSION_DESCRIPTION,
        serialization_alias=SUSPENSION_DESCRIPTION,
        example=INTERNET_ERROR
    )
    suspension_start: datetime = Field(
        ...,
        title=SUSPENSION_START,
        serialization_alias=SUSPENSION_START,
        example=FROM_TIME
    )
    suspension_finish: datetime = Field(
        ...,
        title=SUSPENSION_FINISH,
        serialization_alias=SUSPENSION_FINISH,
        example=TO_TIME
    )
    implementing_measures: str = Field(
        ...,
        max_length=SUSPENSION_IMPLEMENTING_MEASURES,
        title=IMPLEMENTING_MEASURES,
        serialization_alias=IMPLEMENTING_MEASURES,
        example=MEASURES
    )

    @computed_field(alias=SUSPENSION_DURATION)
    @property
    def duration(self) -> PositiveInt | float:
        suspension_finish = time.strptime(self.suspension_finish.strftime(DATE_TIME_FORMAT), DATE_TIME_FORMAT)
        suspension_start = time.strptime(self.suspension_start.strftime(DATE_TIME_FORMAT), DATE_TIME_FORMAT)
        return (time.mktime(suspension_finish) - time.mktime(suspension_start)) / SUSPENSION_DURATION_RESPONSE  # mins

    @field_serializer("created_at", "updated_at")
    def serialize_server_time_to_time_shift(self, server_time: datetime, _info):
        """Отображает сохраненное время сервера с требуемым сдвигом."""
        return (server_time + timedelta(hours=settings.TIMEZONE_OFFSET)).strftime(DATE_TIME_FORMAT)

    class Config:
        """Implement a custom json serializer by using pydantic's custom json encoders.
        Переводит datetime из БД в формат str для удобства отображения."""
        json_encoders = {date: lambda db_date_time: (db_date_time + timedelta(hours=0)).strftime(DATE_FORMAT)}
        from_attributes = True  # in V2: 'orm_mode' has been renamed! In order to serialize ORM-model into schema.


class SuspensionCreateNew(BaseModel):  # todo rename
    """Схема cоздания объекта в БД."""
    risk_accident: RiskAccidentSource
    tech_process: TechProcess  # made changes todo check it
    description: str = Field(
        ...,
        max_length=SUSPENSION_DESCRIPTION_LENGTH,
        title=SUSPENSION_DESCRIPTION,
        serialization_alias=SUSPENSION_DESCRIPTION,
        example=INTERNET_ERROR
    )
    suspension_start: datetime = Field(
        ...,
        title=SUSPENSION_START,
        serialization_alias=SUSPENSION_START,
        example=FROM_TIME
    )
    suspension_finish: datetime = Field(
        ...,
        title=SUSPENSION_FINISH,
        serialization_alias=SUSPENSION_FINISH,
        example=TO_TIME
    )
    implementing_measures: str = Field(
        ...,
        max_length=SUSPENSION_IMPLEMENTING_MEASURES,
        title=IMPLEMENTING_MEASURES,
        serialization_alias=IMPLEMENTING_MEASURES,
        example=MEASURES
    )

    class Config:
        extra = Extra.forbid  # TODO старый метод конфигурации, нужно обновить- model_config = ConfigDict(strict=False)
        json_schema_extra = {
            "example": {
                "risk_accident": ROUTER_ERROR,  # TODO валидация и отображение ошибки???
                "suspension_start": FROM_TIME,
                "suspension_finish": TO_TIME,
                "tech_process": "25",  # TODO валидация и отображение ошибки???
                "description": INTERNET_ERROR,
                "implementing_measures": MEASURES,
            }
        }


class SuspensionResponseNew(SuspensionBaseNew):  # todo rename
    """Схема ответа для простоев."""
    user_id: PositiveInt = Field(..., serialization_alias=USER_ID)
    extra_files: Optional[list] = Field(None, serialization_alias=FILES_SET_TO)


class AnalyticSuspensionResponse(SuspensionBaseNew):  # todo ERRORS
    """Схема ответа для аналитики задач."""
    business_process: str = Field(..., serialization_alias=TECH_PROCESS)
    user_email: str = Field(..., serialization_alias=USER_MAIL)
    user_id: PositiveInt = Field(..., serialization_alias=USER_ID)
    extra_files: list = Field(..., serialization_alias=FILES_SET_TO)


class SuspensionDeletedResponse(BaseModel):
    """Схема ответа после удаления случая простоя."""
    suspension_deleted: list[SuspensionResponseNew] = Field(..., serialization_alias=SUSPENSION_DELETED)  # todo rename
    files_ids: list[int] = Field(..., serialization_alias=FILES_IDS_DELETED)
