"""src/api/schemas.py"""
from datetime import date
from fastapi_users import schemas
from pydantic import BaseModel, Extra, Field, NonNegativeInt


class ResponseBase(BaseModel):
    """Базовый класс для модели ответа."""

    class Config:
        from_attributes = True


class RequestBase(BaseModel):
    """Базовый класс для модели запроса."""

    class Config:
        extra = Extra.forbid


class SuspensionResponse(ResponseBase):
    """Класс модели ответа для Suspension."""

    risk_accident: str
    datetime_start: date
    datetime_finish: date
    tech_process: int
    description: str
    implementing_measures: str
    user_id: int
    created_at: date
    updated_at: date


class SuspensionRequest(RequestBase):
    """Класс модели запроса для Suspension."""
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