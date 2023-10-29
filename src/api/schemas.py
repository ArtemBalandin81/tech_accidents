"""src/api/schemas.py"""
from datetime import datetime, timedelta

from fastapi_users import schemas
from pydantic import BaseModel, Extra, Field, field_serializer, root_validator, validator

from src.core.enums import RiskAccidentSource, TechProcess
from typing_extensions import TypedDict

from .constants import DATE_TIME_FORMAT, FROM_TIME, TO_TIME
from src.settings import settings


class SuspensionBase(BaseModel):
    """Базовая схема."""
    datetime_start: datetime = Field(..., example=FROM_TIME)
    datetime_finish: datetime = Field(..., example=TO_TIME)
    description: str = Field(..., max_length=256, example="Сбой подключения к интернет.")
    implementing_measures: str = Field(..., max_length=256, example="Перезагрузка оборудования.")

    class Config:
        """Implement a custom json serializer by using pydantic's custom json encoders.
        Переводит datetime из БД в формат str для удобства отображения."""
        json_encoders = {datetime: lambda db_date_time: (db_date_time + timedelta(hours=0)).strftime(DATE_TIME_FORMAT)}

class SuspensionResponse(SuspensionBase):
    """Схема ответа для Suspension."""
    risk_accident: str
    tech_process: int  # TODO сериализовать в "25 - ДУ"
    user_id: int  #TODO сериализовать в "user_name_surname"
    created_at: datetime
    updated_at: datetime
    id: int

    @field_serializer("datetime_start", "datetime_finish", "created_at", "updated_at")
    def serialize_server_time_to_time_shift(self, server_time: datetime, _info):
        """Отображает сохраненное время сервера с требуемым сдвигом."""
        return server_time.strftime(DATE_TIME_FORMAT)

    @field_serializer("created_at", "updated_at")
    def serialize_server_time_to_time_shift(self, server_time: datetime, _info):
        """Отображает сохраненное время сервера с требуемым сдвигом."""
        return (server_time + timedelta(hours=settings.TIMEZONE_OFFSET)).strftime(DATE_TIME_FORMAT)

    class Config:
        from_attributes = True  # in V2: 'orm_mode' has been renamed to 'from_attributes'


class SuspensionRequest(SuspensionBase):  # TODO реализовать схему валидации
    """Схема json-запроса для создания Suspension."""
    risk_accident: RiskAccidentSource
    tech_process: TechProcess

    class Config:
        extra = Extra.forbid
        json_schema_extra = {
            "example": {
                "risk_accident": "Риск инцидент: сбой в работе рутера.",  # TODO валидация и отображение ошибки???
                "datetime_start": FROM_TIME,
                "datetime_finish": TO_TIME,
                "tech_process": 25,  # TODO валидация и отображение ошибки???
                "description": "Сбой подключения к интернет.",
                "implementing_measures": "Перезагрузка оборудования.",
            }
        }


class TotalTimeSuspensions(TypedDict):
    """Класс ответа для аналитики за период времени."""

    total_time_suspensions_in_mins: int


class SuspensionAnalytics(BaseModel):
    """Класс ответа для аналитики случаев простоя за период времени."""

    #time_suspensions: TotalTimeSuspensions = {}
    suspensions_in_mins_total: int
    suspensions_total: int
    max_suspension_time_for_period: int
    last_time_suspension: datetime
    last_time_suspension_id: int
    suspensions: list[SuspensionResponse] = {}

    class Config:
        from_attributes = True  # in V2: 'orm_mode' has been renamed to 'from_attributes'
        json_encoders = {datetime: lambda db_date_time: db_date_time.strftime(DATE_TIME_FORMAT)}


class UserRead(schemas.BaseUser[int]):
    pass


class UserCreate(schemas.BaseUserCreate):
    pass


class UserUpdate(schemas.BaseUserUpdate):
    pass
