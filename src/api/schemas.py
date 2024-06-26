"""src/api/schemas.py"""
import time

from fastapi_users import schemas
from pydantic import (BaseModel, Extra, Field, PositiveInt, computed_field,
                      field_serializer)
from src.api.constants import *
from src.core.enums import RiskAccidentSource, TechProcess
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
    description: str = Field(..., max_length=SUSPENSION_DESCRIPTION_LENGTH, example=INTERNET_ERROR)
    implementing_measures: str = Field(..., max_length=SUSPENSION_IMPLEMENTING_MEASURES, example=MEASURES)
    risk_accident: RiskAccidentSource
    tech_process: TechProcess

    class Config:
        extra = Extra.forbid  # TODO старый метод конфигурации, нужно обновить- model_config = ConfigDict(strict=False)
        json_schema_extra = {
            "example": {
                "risk_accident": ROUTER_ERROR,  # TODO валидация и отображение ошибки???
                "datetime_start": FROM_TIME,
                "datetime_finish": TO_TIME,
                "tech_process": "25",  # TODO валидация и отображение ошибки???
                "description": INTERNET_ERROR,
                "implementing_measures": MEASURES,
            }
        }


class SuspensionBase(BaseModel):
    """Базовая схема."""
    id: PositiveInt
    datetime_start: datetime = Field(
        ...,
        title=SUSPENSION_START,
        serialization_alias=SUSPENSION_START,
        example=FROM_TIME
    )
    datetime_finish: datetime = Field(
        ...,
        title=SUSPENSION_FINISH,
        serialization_alias=SUSPENSION_FINISH,
        example=TO_TIME
    )
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

    @computed_field(alias=SUSPENSION_DURATION)
    @property
    def duration(self) -> PositiveInt | float:
        suspension_finish = time.strptime(self.datetime_finish.strftime(DATE_TIME_FORMAT), DATE_TIME_FORMAT)
        suspension_start = time.strptime(self.datetime_start.strftime(DATE_TIME_FORMAT), DATE_TIME_FORMAT)
        return (time.mktime(suspension_finish) - time.mktime(suspension_start)) / SUSPENSION_DURATION_RESPONSE  # mins

    class Config:
        """Implement a custom json serializer by using pydantic's custom json encoders.
        Переводит datetime из БД в формат str для удобства отображения."""
        json_encoders = {datetime: lambda db_date_time: (db_date_time + timedelta(hours=0)).strftime(DATE_TIME_FORMAT)}


class SuspensionResponse(SuspensionBase):
    """Схема ответа для Suspension с использованием response_model."""
    risk_accident: str = Field(..., serialization_alias=RISK_ACCIDENT)
    tech_process: PositiveInt = Field(..., serialization_alias=TECH_PROCESS)
    user_id: PositiveInt = Field(..., serialization_alias=USER_ID)
    created_at: datetime = Field(..., serialization_alias=CREATED)
    updated_at: datetime = Field(..., serialization_alias=UPDATED)

    @field_serializer("created_at", "updated_at")
    def serialize_server_time_to_time_shift(self, server_time: datetime, _info):
        """Отображает сохраненное время сервера с требуемым сдвигом."""
        return (server_time + timedelta(hours=settings.TIMEZONE_OFFSET)).strftime(DATE_TIME_FORMAT)

    class Config:
        from_attributes = True  # in V2: 'orm_mode' has been renamed to 'from_attributes'


class AnalyticResponse(SuspensionBase):
    """Схема ответа для аналитики."""
    risk_accident: str = Field(..., serialization_alias=RISK_ACCIDENT)
    business_process: str = Field(..., serialization_alias=TECH_PROCESS)
    user_email: str = Field(..., serialization_alias=USER_MAIL)
    user_id: PositiveInt = Field(..., serialization_alias=USER_ID)
    created_at: datetime = Field(..., serialization_alias=CREATED)
    updated_at: datetime = Field(..., serialization_alias=UPDATED)

    @field_serializer("created_at", "updated_at")
    def serialize_server_time_to_time_shift(self, server_time: datetime, _info):
        """Отображает сохраненное время сервера с требуемым сдвигом."""
        return (server_time + timedelta(hours=settings.TIMEZONE_OFFSET)).strftime(DATE_TIME_FORMAT)

    class Config:
        from_attributes = True  # in V2: 'orm_mode' has been renamed! In order to serialize ORM-model into schema.


class SuspensionAnalytics(BaseModel):
    """Класс ответа для аналитики случаев простоя за период времени."""

    suspensions_in_mins_total: PositiveInt = Field(..., serialization_alias=MINS_TOTAL)
    suspensions_total: PositiveInt = Field(..., serialization_alias=SUSPENSION_TOTAl)
    suspension_max_time_for_period: PositiveInt = Field(..., serialization_alias=SUSPENSION_MAX_TIME)
    last_time_suspension: datetime = Field(..., serialization_alias=SUSPENSION_LAST_TIME)
    last_time_suspension_id: PositiveInt = Field(..., serialization_alias=SUSPENSION_LAST_ID)
    suspensions_detailed: list[AnalyticResponse] = {}  # todo = Field(..., serialization_alias=???) мн без = {}

    class Config:
        from_attributes = True  # in V2: 'orm_mode' has been renamed! In order to serialize ORM-model into schema.
        json_encoders = {datetime: lambda db_date_time: db_date_time.strftime(DATE_TIME_FORMAT)}


class DBBackupResponse(BaseModel):
    """Класс ответа для бэкапа БД."""
    last_backup: str | None
    first_backup: str | None
    total_backups: PositiveInt
    time: str
