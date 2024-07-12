"""src/api/schemas.py"""

from fastapi_users import schemas
from pydantic import BaseModel, PositiveInt


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


class DBBackupResponse(BaseModel):
    """Класс ответа для бэкапа БД."""
    last_backup: str | None
    first_backup: str | None
    total_backups: PositiveInt
    time: str
