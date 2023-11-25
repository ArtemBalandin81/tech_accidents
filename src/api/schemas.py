"""src/api/schemas.py"""
from datetime import datetime, timedelta

from fastapi_users import schemas
from pydantic import BaseModel, EmailStr, Extra, Field, field_serializer, computed_field, root_validator, validator

from src.core.enums import RiskAccidentSource, TechProcess
from typing_extensions import TypedDict

from .constants import DATE_TIME_FORMAT, FROM_TIME, TO_TIME
from src.settings import settings


# https://github.com/fastapi-users/fastapi-users/blob/master/fastapi_users/schemas.py
class UserRead(schemas.BaseUser[int]):
    """Pydantic schemas FastApi Users."""
    # id: models.ID
    # email: EmailStr
    # is_active: bool = True
    # is_superuser: bool = False
    # is_verified: bool = False
    pass


class UserCreate(schemas.BaseUserCreate):
    """Pydantic schemas FastApi Users."""
    # email: EmailStr
    # password: str
    # is_active: Optional[bool] = True
    # is_superuser: Optional[bool] = False
    # is_verified: Optional[bool] = False
    pass


class UserUpdate(schemas.BaseUserUpdate):
    """Pydantic schemas FastApi Users."""
    # password: Optional[str] = None
    # email: Optional[EmailStr] = None
    # is_active: Optional[bool] = None
    # is_superuser: Optional[bool] = None
    # is_verified: Optional[bool] = None
    pass


class SuspensionRequest(BaseModel):  # TODO реализовать схему валидации
    """Схема json-запроса для создания Suspension."""
    datetime_start: datetime = Field(..., example=FROM_TIME)
    datetime_finish: datetime = Field(..., example=TO_TIME)
    description: str = Field(..., max_length=256, example="Сбой подключения к интернет.")
    implementing_measures: str = Field(..., max_length=256, example="Перезагрузка оборудования.")
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


class SuspensionBase(BaseModel):
    """Базовая схема."""
    id: int
    datetime_start: datetime = Field(..., example=FROM_TIME)
    datetime_finish: datetime = Field(..., example=TO_TIME)
    description: str = Field(..., max_length=256, example="Сбой подключения к интернет.")
    implementing_measures: str = Field(..., max_length=256, example="Перезагрузка оборудования.")

    class Config:
        """Implement a custom json serializer by using pydantic's custom json encoders.
        Переводит datetime из БД в формат str для удобства отображения."""
        json_encoders = {datetime: lambda db_date_time: (db_date_time + timedelta(hours=0)).strftime(DATE_TIME_FORMAT)}


class SuspensionResponse(SuspensionBase):
    """Схема ответа для Suspension с использованием response_model."""
    risk_accident: str
    tech_process: int
    user_id: int
    created_at: datetime
    updated_at: datetime

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


class AnalyticResponse(SuspensionBase):
    """Схема ответа для аналитики."""
    risk_accident: str
    # tech_process: int
    business_process: str
    user_email: str
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # in V2: 'orm_mode' has been renamed to 'from_attributes'


class SuspensionAnalytics(BaseModel):
    """Класс ответа для аналитики случаев простоя за период времени."""

    suspensions_in_mins_total: int
    suspensions_total: int
    max_suspension_time_for_period: int
    last_time_suspension: datetime
    last_time_suspension_id: int
    # suspensions: list[SuspensionResponse] = {}
    suspensions_detailed: list[AnalyticResponse] = {}

    class Config:
        from_attributes = True  # in V2: 'orm_mode' has been renamed to 'from_attributes'
        json_encoders = {datetime: lambda db_date_time: db_date_time.strftime(DATE_TIME_FORMAT)}
