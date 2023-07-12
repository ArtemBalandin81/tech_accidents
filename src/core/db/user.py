"""src/core/db/user.py"""
from typing import Optional, Union

from fastapi import Depends, Request
from fastapi_users import (
    BaseUserManager, FastAPIUsers, IntegerIDMixin, InvalidPasswordException
)
from fastapi_users.authentication import (
    AuthenticationBackend, BearerTransport, JWTStrategy
)
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

# from app.core.config import settings
from src.settings import settings
# from app.core.db import get_async_session
from src.core.db.db import get_session  # NotaBena!!!
# from app.models.user import User
from src.core.db.models import User
# from app.schemas.user import UserCreate
from src.api.schemas import UserCreate

#2. асинхронный генератор get_user_db: обеспечивает доступ к БД чз SQLAlchemy
#используется как зависимость (dependency) для объекта класса UserManager
async def get_user_db(session: AsyncSession = Depends(get_session)):
    yield SQLAlchemyUserDatabase(session, User)

#3.1 Транспорт: передавать токен будем чз заголовок HTTP-запроса Authorization:
# Bearer. Указываем URL эндпоинта для получения токена.
bearer_transport = BearerTransport(tokenUrl='auth/jwt/login')

#3.2 Определяем стратегию: хранение токена в виде JWT.
def get_jwt_strategy() -> JWTStrategy:
    # В специальный класс из настроек приложения
    # передаётся секретное слово, используемое для генерации токена.
    # Вторым аргументом передаём срок действия токена в секундах.
    return JWTStrategy(secret=settings.SECRET_KEY, lifetime_seconds=3600)

#3.3 Создаём объект бэкенда аутентификации с выбранными параметрами.
auth_backend = AuthenticationBackend(
    name='jwt',  # Произвольное имя бэкенда (должно быть уникальным).
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

#4. Добавьте класс UserManager и корутину, возвращающую объект этого класса.
class UserManager(IntegerIDMixin, BaseUserManager[User, int]):

    # Описываем свои условия валидации пароля. При успешной валидации функция
    # ничего не возвращает.При ошибке валидации будет вызван специальный класс
    # ошибки InvalidPasswordException.
    async def validate_password(
        self,
        password: str,
        user: Union[UserCreate, User],
    ) -> None:
        if len(password) < 6:
            raise InvalidPasswordException(
                reason='Password should be at least 6 characters'
            )
        if user.email in password:
            raise InvalidPasswordException(
                reason='Password should not contain e-mail'
            )

    # Пример метода для действий после успешной регистрации пользователя.
    async def on_after_register(
            self, user: User, request: Optional[Request] = None
    ):
        # Вместо print здесь можно было бы настроить отправку письма.
        print(f'Пользователь {user.email} зарегистрирован.')

# Корутина, возвращающая объект класса UserManager.
async def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db)

#5. Создаём объект класса FastAPIUsers — это центральный объект библиотеки,
# связывающий объект класса UserManager и бэкенд аутентификации.
fastapi_users = FastAPIUsers[User, int](
    get_user_manager,
    [auth_backend],
)

#6. Методы класса FastAPIUsers, которые используются в Dependency Injection
# для получения текущего пользователя при выполнении запросов, а также для
# разграничения доступа: некоторые эндпоинты будут доступны только суперюзерам.
unauthorized_user = fastapi_users.current_user(optional=True)
current_user = fastapi_users.current_user(active=True)
current_superuser = fastapi_users.current_user(active=True, superuser=True)