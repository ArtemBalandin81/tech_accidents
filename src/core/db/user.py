"""src/core/db/user.py"""
from typing import Optional, Union

import structlog
from fastapi import Depends, Request
from fastapi_users import (BaseUserManager, FastAPIUsers, IntegerIDMixin,
                           InvalidPasswordException)
from fastapi_users.authentication import (AuthenticationBackend,
                                          BearerTransport, JWTStrategy)
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.constants import (IS_REGISTERED, LOGIN, PASSWORD_EMAIL_WARNING,
                               PASSWORD_LENGTH_WARNING)
from src.api.schemas import UserCreate
from src.core.db.db import get_session
from src.core.db.models import User
from src.settings import settings

log = structlog.get_logger()


# Асинхронный генератор get_user_db: дает доступ к БД чз SQLAlchemy как (dependency) для объекта класса UserManager
async def get_user_db(session: AsyncSession = Depends(get_session)):
    yield SQLAlchemyUserDatabase(session, User)

# Транспорт: токен передается чз заголовок HTTP-запроса Authorization: Bearer. URL эндпоинта для получения токена.
bearer_transport = BearerTransport(tokenUrl=LOGIN)


# Стратегия: хранение токена в виде JWT.
def get_jwt_strategy() -> JWTStrategy:
    # В специальный класс из настроек приложения передаётся секретное слово, используемое для генерации токена.
    # Вторым аргументом передаём срок действия токена в секундах.
    return JWTStrategy(secret=settings.SECRET_KEY, lifetime_seconds=settings.TOKEN_AUTH_LIFETIME_SEC)


# Создаём объект бэкенда аутентификации с выбранными параметрами.
auth_backend = AuthenticationBackend(
    name='jwt',  # Произвольное имя бэкенда (должно быть уникальным).
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)


# Добавляем класс UserManager и корутину, возвращающую объект этого класса.
class UserManager(IntegerIDMixin, BaseUserManager[User, int]):

    # Описываем свои условия валидации пароля. При успешной валидации функция ничего не возвращает.
    # При ошибке валидации будет вызван специальный класс ошибки InvalidPasswordException.
    async def validate_password(
        self,
        password: str,
        user: Union[UserCreate, User],
    ) -> None:
        if len(password) < 6:
            raise InvalidPasswordException(reason=PASSWORD_LENGTH_WARNING)
        if user.email in password:
            raise InvalidPasswordException(reason=PASSWORD_EMAIL_WARNING)

    # Действия после успешной регистрации пользователя: тут можно настроить отправку письма
    async def on_after_register(
            self, user: User, request: Optional[Request] = None
    ):
        await log.ainfo("{}{}".format(user.email, IS_REGISTERED))


# Корутина, возвращающая объект класса UserManager.
async def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db)

# Создаём центральный объект класса FastAPIUsers, связывающий объект класса UserManager и бэкенд аутентификации.
fastapi_users = FastAPIUsers[User, int](
    get_user_manager,
    [auth_backend],
)

# Методы класса FastAPIUsers, которые используются в Dependency Injection для получения текущего пользователя
# при выполнении запросов, а также для разграничения доступа: некоторые эндпоинты будут доступны только суперюзерам.
unauthorized_user = fastapi_users.current_user(optional=True)
current_user = fastapi_users.current_user(active=True)
current_superuser = fastapi_users.current_user(active=True, superuser=True)
