"""
Файл для создания асинхронных тестов: tests/test_routes/test_2.py
pytest -s -W ignore::DeprecationWarning
pytest -vs -W ignore::DeprecationWarning --asyncio-mode=strict
https://anyio.readthedocs.io/en/stable/testing.html
"""
from pprint import pprint

import pytest
import structlog
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger().bind(file_name=__file__)


import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.db.models import (Base, FileAttached, Suspension,
                                SuspensionsFiles, Task, TasksFiles, User)
from src.settings import settings

pytestmark = pytest.mark.anyio  # make all test mark with `anyio`


# @pytest.mark.anyio  # pytestmark = pytest.mark.anyio  == make all test mark with `anyio`
async def test_test_url(async_client):
    """Тестирует сервисный эндпоинт проверки доступности сайтов: __/api/services/test_url__"""
    url = "https://agidel-am.ru/"
    api_url = "/api/services/test_url"
    async with async_client as ac:
        response = await ac.get(api_url, params={"url": url})
    assert response.status_code == 200, f"api: test_url status code {response.status_code} is not 200"
    await log.ainfo("test_info:", response_json=response.json(), url=response.url)
    pprint(f'response_json: {response.json()}')

# todo в цикле, словаре сделать тест нескольких эндпоинтов неавторизованным пользователем
# todo сделай красиво в цикле по словарю как было в спринте, постарайся!!!
async def test_unauthorized_get_urls(async_client: AsyncClient, async_db: AsyncSession) -> None:
    """Тестирует доступ к пользовательским эндпоинтам неавторизованным пользователем"""
    data = {"email": "testuser@nofoobar.com", "password": "testing_testing"}
    users_me_url = "/api/users/me"
    test_url = "/api/services/test_url"
    db_backups_url = "/api/services/db_backup"
    a = "/api/auth/jwt/login"  # todo
    b = "/api/auth/jwt/logout"  # todo + проверить регом
    c_get = "/api/users/{id}"  # todo + проверить регом
    b_patch = "/api/users/{id}"  # todo + проверить регом
    e = "/api/users"  # todo + проверить админом!!!

    async with async_client as ac:
        # response = await ac.patch(api_url, json=data)
        response_get_users_me = await ac.get(users_me_url)
        response_patch_users_me = await ac.patch(users_me_url, json=data)
        response_test_url = await ac.get(test_url, params={"url": "https://agidel-am.ru/"})
        response_db_backups = await ac.get(db_backups_url)

    assert response_get_users_me.status_code == 401, f"Unauthorized get {users_me_url} but shouldn't"
    await log.ainfo("get_users_me", response_json=response_get_users_me.json(), url=response_get_users_me.url)

    assert response_patch_users_me.status_code == 401, f"Unauthorized patch {users_me_url} but shouldn't"
    await log.ainfo("patch_users_me", response_json=response_patch_users_me.json(), url=response_patch_users_me.url)

    assert response_test_url.status_code == 200, f"Unauthorized couldn't get {test_url} but should"
    await log.ainfo("get_test_url", response_json=response_test_url.json(), url=response_test_url.url)

    assert response_db_backups.status_code == 401, f"Unauthorized get {db_backups_url} but shouldn't"
    await log.ainfo("get_db_backups", response_json=response_db_backups.json(), url=response_db_backups.url)



async def test_create_user(async_client: AsyncClient, async_db: AsyncSession) -> None:
    """Тестирует эндпоинт регистрации пользователей: __/api/auth/register__"""
    email = "testuser@nofoobar.com"
    password = "testing_testing"
    data = {"email": email, "password": password, "is_superuser": True}
    api_url = "/api/auth/register"
    async with async_client as ac:
        response = await ac.post(api_url, json=data)
    assert response.status_code == 201, f"api: user register status code {response.status_code} is not 201"
    user_created = await async_db.scalar(select(User).where(User.email == email))
    assert email == user_created.email, f"created user {user_created.email} doesn't meet expectations: {email}"
    assert response.json()["id"] == user_created.id, f"user id {user_created.id} doesn't meet {response.json()['id']}"
    assert response.json()["is_superuser"] == user_created.is_superuser, "user is_superuser doesn't meet expectations"
    assert user_created.is_superuser is False, f"user_created.is_superuser: {user_created.is_superuser} is not False"
    await log.ainfo(
        "post_auth_register:", response=response.json(), url=response.url,
        user_email=user_created.email, user_id=user_created.id, super_user=user_created.is_superuser,
    )
    # pprint(f'response_json: {response.json()}')

async def test_user_and_super_user_exist(
        async_client: AsyncClient, async_db: AsyncSession, super_user_orm: User, user_orm: User
) -> None:
    """Тестирует, что в БД созданы супер-пользователь и пользователь."""
    assert super_user_orm.is_superuser is True, "super_user_orm is not super_user but should"
    assert super_user_orm.email == "super_user_fixture@nofoobar.com", "email of super_user_orm is not correct"
    assert user_orm.is_superuser is False, "user_orm is super_user but shouldn't"
    assert user_orm.email == "user_fixture@nofoobar.com", "email of user_orm doesn't meet expectations"
    await log.ainfo(
        "test_info:",
        super_user_email=super_user_orm.email,
        super_user_id=super_user_orm.id,
        is_super_user_superuser=super_user_orm.is_superuser,
        user_email=user_orm.email,
        user_id=user_orm.id,
        is_user_superuser=user_orm.is_superuser
    )
    # pprint(f'super_user_hashed_password: {super_user_orm.hashed_password}')

async def test_authorized_patch_users_me(async_client: AsyncClient, async_db: AsyncSession) -> None:
    """Тестирует эндпоинт патча пользователя: __/api/users/me__"""
    data = {"email": "testuser@nofoobar.com", "password": "testing_testing"}
    api_url = "/api/users/me"
    async with async_client as ac:
        # response = await ac.patch(api_url, json=data)  # todo finish
        response = await ac.get(api_url)  # todo finish
    assert response.status_code == 401
    await log.ainfo("patch_users_me", response_json=response.json(), url=response.url)
    # pprint(f'response_json: {response.json()}')


# def test_authorized_get_db_backup(async_client: AsyncClient):  # todo нужен авторизованный пользователь
#     """Тестирует сервисный эндпоинт бэкапа БД авторизованным пользователем: __/api/services/db_backup__"""
#     api_url = "/api/services/db_backup"
#     # response = client.get(api_url)
#     async with async_client as ac:
#         response = await ac.get(api_url)
#     # assert response.status_code == 200
#     pprint(f'response: {response}')
#     pprint(f'response_json: {response.json()}')
#     pprint(f'response_url: {response.url}')