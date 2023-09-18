"""src/api/schemas.py"""
from datetime import datetime, timedelta, timezone

from fastapi_users import schemas
from pydantic import BaseModel, Extra, Field

from src.core.db.models import Suspension
from src.core.enums import RiskAccidentSource, TechProcess
from typing import Optional

from .constants import DATE_TIME_FORMAT, FROM_TIME, TO_TIME


def convert_server_datetime_to_local_time(db_date_time: datetime) -> str:
    return (db_date_time + timedelta(hours=5)).strftime(DATE_TIME_FORMAT)

def transform_to_utc_datetime(db_date_time: datetime) -> str:
    return (db_date_time.astimezone(tz=None)).strftime(DATE_TIME_FORMAT)


class SuspensionBase(BaseModel):
    """Базовый класс."""
    datetime_start: datetime = Field(..., example=FROM_TIME)
    datetime_finish: datetime = Field(..., example=TO_TIME)
    description: str = Field(..., max_length=256, example="Сбой подключения к интернет.")
    implementing_measures: str = Field(..., max_length=256, example="Перезагрузка оборудования.")

    class Config:
        """Implement a custom json serializer by using pydantic's custom json encoders.
        Переводит datetime из БД в формат str для удобства отображения."""
        #json_encoders = {datetime: lambda db_date_time: (db_date_time + timedelta(hours=5)).strftime(DATE_TIME_FORMAT)}

class SuspensionResponse(SuspensionBase):
    """Класс модели ответа для Suspension."""
    risk_accident: str
    tech_process: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        orm_mode = True
        #json_encoders = {datetime: lambda server_time_shift: server_time_shift + timedelta(hours=5)}
        #json_encoders = {datetime: lambda db_date_time: db_date_time + timedelta(hours=5)}
        json_encoders = {datetime: transform_to_utc_datetime}


class SuspensionRequest(SuspensionBase):
    """Класс модели запроса для Suspension."""

    risk_accident: RiskAccidentSource
    tech_process: TechProcess

    class Config:
        extra = Extra.forbid
        json_schema_extra = {
            "example": {
                "risk_accident": "ROUTER",
                "datetime_start": "31-12-2025: HH:MM:SS",
                "datetime_finish:": "31-12-2025: HH:MM:SS",
                "tech_process": "25",
                "description": "Сбой подключения к интернет.",
                "implementing_measures": "Перезагрузка оборудования.",
            }
        }



#
#     id: NonNegativeInt = Field(...)
#     title: StrictStr = Field(...)
#     name_organization: StrictStr = Field(...)
#     deadline: date = Field(..., format=DATE_FORMAT)
#     category_id: NonNegativeInt = Field(...)
#     bonus: NonNegativeInt = Field(...)
#     location: StrictStr = Field(...)
#     link: StrictStr = Field(...)
#     description: Optional[StrictStr] = None
#
#     class Config:
#         json_schema_extra = {
#             "example": {
#                 "id": 1,
#                 "title": "Task Title",
#                 "name_organization": "My Organization",
#                 "deadline": "2025-12-31",
#                 "category_id": 1,
#                 "bonus": 5,
#                 "location": "My Location",
#                 "link": "https://example.com",
#                 "description": "Task description",
#             }
#         }


class UserRead(schemas.BaseUser[int]):
    pass


class UserCreate(schemas.BaseUserCreate):
    pass


class UserUpdate(schemas.BaseUserUpdate):
    pass