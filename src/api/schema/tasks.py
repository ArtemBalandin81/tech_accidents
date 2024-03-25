"""src/api/schemas/tasks.py"""
import time
from datetime import date

from fastapi_users import schemas
from pydantic import BaseModel, EmailStr, Extra, Field, field_serializer, computed_field, root_validator, validator

from src.core.enums import RiskAccidentSource, TechProcess
from typing_extensions import TypedDict
from src.api.constants import *
from src.settings import settings


# class SuspensionRequest(BaseModel):  # TODO реализовать схему валидации
#     """Схема json-запроса для создания Suspension."""
#     datetime_start: datetime = Field(..., example=FROM_TIME)
#     datetime_finish: datetime = Field(..., example=TO_TIME)
#     description: str = Field(..., max_length=256, example=INTERNET_ERROR)
#     implementing_measures: str = Field(..., max_length=256, example=MEASURES)
#     risk_accident: RiskAccidentSource
#     tech_process: TechProcess
#
#     class Config:
#         extra = Extra.forbid  # TODO старый метод конфигурации, нужно обновить- model_config = ConfigDict(strict=False)
#         json_schema_extra = {
#             "example": {
#                 "risk_accident": ROUTER_ERROR,  # TODO валидация и отображение ошибки???
#                 "datetime_start": FROM_TIME,
#                 "datetime_finish": TO_TIME,
#                 "tech_process": 25,  # TODO валидация и отображение ошибки???
#                 "description": INTERNET_ERROR,
#                 "implementing_measures": MEASURES,
#             }
#         }


class TaskBase(BaseModel):
    """Базовая схема задач."""
    id: int
    task_start: date = Field(
        ...,
        title=TASK_START,
        serialization_alias=TASK_START,
        example=FROM_TIME
    )
    deadline: date = Field(
        ...,
        title=TASK_FINISH,
        serialization_alias=TASK_FINISH,
        example=TO_TIME
    )

    description: str = Field(
        ...,
        max_length=256,
        title=TASK_DESCRIPTION,
        serialization_alias=TASK_DESCRIPTION,
        example=TASK_DESCRIPTION
    )

    @computed_field(alias=TASK_DURATION)
    @property
    def duration(self) -> int | float:
        task_finish = time.strptime(self.deadline.strftime(DATE_TIME_FORMAT), DATE_TIME_FORMAT)
        today = time.strptime(date.today().strftime(DATE_TODAY_FORMAT), DATE_TODAY_FORMAT)
        return (time.mktime(task_finish) - time.mktime(today))/(60*60*24)  # in days

    class Config:
        """Implement a custom json serializer by using pydantic's custom json encoders.
        Переводит datetime из БД в формат str для удобства отображения."""
        json_encoders = {date: lambda db_date_time: (db_date_time + timedelta(hours=0)).strftime(DATE_FORMAT)}


class TaskResponse(TaskBase):
    """Схема ответа для задач."""
    task: str = Field(..., serialization_alias=TASK)
    tech_process: int = Field(..., serialization_alias=TECH_PROCESS)
    user_id: int = Field(..., serialization_alias=TASK_USER_ID)
    executor: int = Field(..., serialization_alias=TASK_EXECUTOR)
    created_at: datetime = Field(..., serialization_alias=CREATED)
    updated_at: datetime = Field(..., serialization_alias=UPDATED)
    is_archived: bool

    @field_serializer("created_at", "updated_at")
    def serialize_server_time_to_time_shift(self, server_time: datetime, _info):
        """Отображает сохраненное время сервера с требуемым сдвигом."""
        return (server_time + timedelta(hours=settings.TIMEZONE_OFFSET)).strftime(DATE_TIME_FORMAT)

    class Config:
        from_attributes = True  # in V2: 'orm_mode' has been renamed to 'from_attributes'


class AnalyticTaskResponse(TaskBase):
    """Схема ответа для аналитики."""
    task: str = Field(..., serialization_alias=TASK)
    # tech_process: int
    business_process: str = Field(..., serialization_alias=TECH_PROCESS)
    user_email: str = Field(..., serialization_alias=USER_MAIL)
    # user_id: int = Field(..., serialization_alias=USER_ID)
    executor_email: str = Field(..., serialization_alias=TASK_EXECUTOR_MAIL)
    # executor: int = Field(..., serialization_alias=TASK_EXECUTOR)
    created_at: datetime = Field(..., serialization_alias=CREATED)
    updated_at: datetime = Field(..., serialization_alias=UPDATED)
    is_archived: bool = Field(..., serialization_alias=IS_ARCHIVED)

    class Config:
        from_attributes = True  # in V2: 'orm_mode' has been renamed to 'from_attributes'