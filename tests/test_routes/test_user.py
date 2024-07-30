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


#@pytest.mark.anyio  # pytestmark = pytest.mark.anyio  == make all test mark with `anyio`
async def test_test_url(async_client):
    """Тестирует сервисный эндпоинт проверки доступности сайтов: __/api/services/test_url__"""
    url = "https://agidel-am.ru/"
    api_url = "/api/services/test_url"
    async with async_client as ac:
        response = await ac.get(api_url, params={"url": url})
    assert response.status_code == 200
    await log.ainfo("test_info:", response_json=response.json(), url=response.url)
    # pprint(f'response_json: {response.json()}')


async def test_create_user(async_client: AsyncClient, async_db: AsyncSession) -> None:
    """Тестирует эндпоинт регистрации пользователей: __/api/auth/register__"""
    email = "testuser@nofoobar.com"
    password = "testing_testing"
    data = {"email": email, "password": password, "is_superuser": True}
    api_url = "/api/auth/register"
    async with async_client as ac:
        response = await ac.post(api_url, json=data)
    assert response.status_code == 201
    user_created = await async_db.scalar(select(User).where(User.email == email))
    assert email == user_created.email
    assert response.json()["id"] == user_created.id
    assert response.json()["is_superuser"] == user_created.is_superuser
    assert user_created.is_superuser is False
    await log.ainfo(
        "test_info:", response=response.json(), url=response.url,
        user_email=user_created.email, user_id=user_created.id, super_user=user_created.is_superuser,
    )
    # pprint(f'response_json: {response.json()}')

async def test_user_and_super_user_exist(
        async_client: AsyncClient, async_db: AsyncSession, super_user_orm: User, user_orm: User
) -> None:
    """Тестирует, что в БД созданы супер-пользователь и пользователь."""
    assert super_user_orm.is_superuser is True
    assert super_user_orm.email == "super_user_fixture@nofoobar.com"
    assert user_orm.is_superuser is False
    assert user_orm.email == "user_fixture@nofoobar.com"
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

# async def test_assign_super_user(async_client: AsyncClient, async_db: AsyncSession) -> None:  # todo test super_user
#     """Тестирует эндпоинт патча пользователя: __???__"""
#     data = {"email": "testuser@nofoobar.com", "password": "testing_testing"}
#     api_url = "/api/auth/register"
#     async with async_client as ac:
#         response = await ac.post(api_url, json=data)
#     assert response.status_code == 201
#     await log.ainfo("response", response_json=response.json(), url=response.url)
#     # pprint(f'response_json: {response.json()}')





# def test_db_backup(async_client: AsyncClient):  # todo пока не дает, т.к. нет авторизованного пользователя
#     """Тестирует сервисный эндпоинт бэкапа БД авторизованным пользователем: __/api/services/db_backup__"""
#     api_url = "/api/services/db_backup"
#     # response = client.get(api_url)
#     async with async_client as ac:
#         response = await ac.get(api_url)
#     # assert response.status_code == 200
#     pprint(f'response: {response}')
#     pprint(f'response_json: {response.json()}')
#     pprint(f'response_url: {response.url}')