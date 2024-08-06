"""src/api/endpoints/user.py"""
from fastapi import APIRouter, Depends, HTTPException, status
from src.api.schemas import UserCreate, UserRead, UserUpdate
from src.api.services import UsersService
from src.core.db.user import auth_backend, current_superuser, fastapi_users

router = APIRouter()

router.include_router(
    fastapi_users.get_auth_router(auth_backend),  # В роутер аутентификации передается объект бэкенда аутентификации.
    prefix='/auth/jwt',
    tags=['auth'],
)
router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix='/auth',
    tags=['auth'],
)
router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix='/users',
    tags=['users'],
)


@router.get(
    "/users",
    dependencies=[Depends(current_superuser)],
    description="Получить всех активных пользователей (только админ).",  # todo в константы
    summary="Список всех активных пользователей (только админ).",
    tags=['users'],  # todo в константы
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Missing token or inactive user.",
        },
        status.HTTP_403_FORBIDDEN: {
            "description": "Not a superuser.",
        },
    },
)
async def get_all_active(
    user_service: UsersService = Depends(),
) -> str:
    return await user_service.get_all_active()


@router.delete(
    '/users/{id}',  # todo в константы
    tags=['users'],
    deprecated=True  # Параметр, который показывает, что метод устарел.
)
def delete_user(id: str):
    """Не используйте удаление, деактивируйте пользователей."""
    raise HTTPException(
        status_code=405,  # 405 ошибка - метод не разрешен.
        detail="Удаление пользователей запрещено!"
    )
