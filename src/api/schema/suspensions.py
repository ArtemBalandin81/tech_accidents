"""src/api/schema/suspensions.py"""

import time
from datetime import date
from typing import Optional

from pydantic import (BaseModel, Extra, Field, PositiveInt, computed_field,
                      field_serializer)
from src.api.constants import *
from src.core.enums import RiskAccidentSource, TechProcess
from src.settings import settings


class SuspensionBase(BaseModel):
    """Базовая схема простоев."""
    id: PositiveInt
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
    risk_accident: RiskAccidentSource = Field(..., serialization_alias=RISK_ACCIDENT)
    tech_process: PositiveInt = Field(..., serialization_alias=TECH_PROCESS)
    description: str = Field(
        ...,
        max_length=SUSPENSION_DESCRIPTION_LENGTH,
        title=SUSPENSION_DESCRIPTION,
        serialization_alias=SUSPENSION_DESCRIPTION,
        example=INTERNET_ERROR
    )
    implementing_measures: str = Field(
        ...,
        max_length=SUSPENSION_IMPLEMENTING_MEASURES,
        title=IMPLEMENTING_MEASURES,
        serialization_alias=IMPLEMENTING_MEASURES,
        example=MEASURES
    )
    created_at: datetime = Field(..., serialization_alias=CREATED)
    updated_at: datetime = Field(..., serialization_alias=UPDATED)

    @computed_field(alias=SUSPENSION_DURATION)
    @property
    def duration(self) -> PositiveInt | float:
        suspension_finish = time.strptime(self.suspension_finish.strftime(DATE_TIME_FORMAT), DATE_TIME_FORMAT)
        suspension_start = time.strptime(self.suspension_start.strftime(DATE_TIME_FORMAT), DATE_TIME_FORMAT)
        return (time.mktime(suspension_finish) - time.mktime(suspension_start)) / SUSPENSION_DURATION_RESPONSE  # mins

    @field_serializer("created_at", "updated_at")
    def serialize_server_time_with_time_shift_for_create_update(self, server_time: datetime, _info):
        """Отображает сохраненное время сервера с требуемым сдвигом."""
        return (server_time + timedelta(hours=settings.TIMEZONE_OFFSET)).strftime(DATE_TIME_FORMAT)

    @field_serializer("suspension_start", "suspension_finish")
    def serialize_server_time_with_time_shift_for_start_finish(self, server_time: datetime, _info):
        """Отображает сохраненное время сервера с требуемым сдвигом."""
        return server_time.strftime(DATE_TIME_FORMAT)

    class Config:
        """Implement a custom json serializer by using pydantic's custom json encoders.
        Переводит datetime из БД в формат str для удобства отображения."""
        json_encoders = {date: lambda db_date_time: (db_date_time + timedelta(hours=0)).strftime(DATE_FORMAT)}
        from_attributes = True  # in V2: 'orm_mode' has been renamed! In order to serialize ORM-model into schema.


class SuspensionCreate(BaseModel):
    """Схема cоздания объекта в БД."""
    risk_accident: RiskAccidentSource
    tech_process: TechProcess
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
        extra = Extra.forbid
        json_schema_extra = {
            "example": {
                "risk_accident": ROUTER_ERROR,
                "suspension_start": FROM_TIME,
                "suspension_finish": TO_TIME,
                "tech_process": "25",
                "description": INTERNET_ERROR,
                "implementing_measures": MEASURES,
            }
        }


class SuspensionResponse(SuspensionBase):
    """Схема ответа для простоев."""
    user_id: PositiveInt = Field(..., serialization_alias=USER_ID)
    extra_files: Optional[list] = Field(None, serialization_alias=FILES_SET_TO)


class AnalyticSuspensionResponse(SuspensionBase):
    """Схема ответа для аналитики случаев простоя."""
    business_process: str = Field(..., serialization_alias=TECH_PROCESS)
    user_email: str = Field(..., serialization_alias=USER_MAIL)
    user_id: PositiveInt = Field(..., serialization_alias=USER_ID)
    extra_files: list = Field(..., serialization_alias=FILES_SET_TO)


class SuspensionDeletedResponse(BaseModel):
    """Схема ответа после удаления случая простоя."""
    suspension_deleted: list[SuspensionResponse] = Field(..., serialization_alias=SUSPENSION_DELETED)
    files_ids: list[int] = Field(..., serialization_alias=FILES_IDS_DELETED)


class AnalyticsSuspensions(BaseModel):
    """Класс ответа для аналитики случаев простоя за период времени."""

    suspensions_in_mins_total: PositiveInt = Field(..., serialization_alias=MINS_TOTAL)
    suspensions_total: PositiveInt = Field(..., serialization_alias=SUSPENSION_TOTAl)
    suspension_max_time_for_period: PositiveInt = Field(..., serialization_alias=SUSPENSION_MAX_TIME)
    last_time_suspension: datetime = Field(..., serialization_alias=SUSPENSION_LAST_TIME)
    last_time_suspension_id: PositiveInt = Field(..., serialization_alias=SUSPENSION_LAST_ID)
    suspensions_list: list[AnalyticSuspensionResponse] = Field(..., serialization_alias=SUSPENSION_LIST)

    class Config:
        from_attributes = True  # in V2: 'orm_mode' has been renamed! In order to serialize ORM-model into schema.
        json_encoders = {datetime: lambda db_date_time: db_date_time.strftime(DATE_TIME_FORMAT)}
