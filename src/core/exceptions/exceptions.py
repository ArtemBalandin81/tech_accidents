"""src/core/exceptions/exceptions.py"""
from http import HTTPStatus
from typing import Any

from src.api.constants import ALREADY_EXISTS, NOT_FOUND, WITH_ID
from src.core.db.models import Base as DatabaseModel
from starlette.exceptions import HTTPException


class ApplicationException(HTTPException):
    status_code: int = None
    detail: str = None
    headers: dict[str, Any] = None

    def __init__(self):
        super().__init__(status_code=self.status_code, detail=self.detail, headers=self.headers)


class NotFoundException(ApplicationException):
    def __init__(self, object_name: str, object_id: int):
        self.status_code = HTTPStatus.NOT_FOUND
        self.detail = "{}{}{}{}".format(object_name, WITH_ID, object_id, NOT_FOUND)


class AlreadyExistsException(ApplicationException):
    def __init__(self, obj: DatabaseModel):
        self.status_code = HTTPStatus.BAD_REQUEST
        self.detail = "{}{}".format(obj, ALREADY_EXISTS)
