"""
Асинхронных тесты сервисных эндпоинтов и работы с пользователями: tests/test_routes/test_2.py
pytest -s -W ignore::DeprecationWarning
pytest -k test_unauthorized_get_urls -vs
https://anyio.readthedocs.io/en/stable/testing.html
"""

import pytest
import structlog
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger().bind(file_name=__file__)

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.db.models import User
from src.settings import settings

pytestmark = pytest.mark.anyio  # make all test mark with `anyio`


# @pytest.mark.anyio  # pytestmark = pytest.mark.anyio  == make all test mark with `anyio`
async def test_test_url(async_client):
    """
    Тестирует сервисный эндпоинт проверки доступности сайтов: __/api/services/test_url__
    pytest -k test_test_url -vs
    """
    url = "https://agidel-am.ru/"
    api_url = "/api/services/test_url"
    async with async_client as ac:
        response = await ac.get(api_url, params={"url": url})
    assert response.status_code == 200, f"api: test_url status code {response.status_code} is not 200"
    await log.ainfo("test_info:", response=response.json(), url=response.url)

# todo в цикле, словаре сделать тест нескольких эндпоинтов неавторизованным пользователем
# todo сделай красиво в цикле по словарю как было в спринте, постарайся!!!
async def test_unauthorized_get_urls(async_client: AsyncClient, async_db: AsyncSession) -> None:
    """
    Тестирует доступ к пользовательским эндпоинтам неавторизованным пользователем:
    pytest -k test_unauthorized_get_urls -vs
    """
    data_patch = {"email": "testuser@nofoobar.com", "password": "testing_testing"}
    login_data = {"username": "some_unknown@username.com", "password": "unknown_password"}
    users_me_url = "/api/users/me"
    test_url = "/api/services/test_url"
    db_backups_url = "/api/services/db_backup"
    login_url = "/api/auth/jwt/login"
    logout_url = "/api/auth/jwt/logout"
    c_get = "/api/users/{id}"  # todo + проверить регом
    b_patch = "/api/users/{id}"  # todo + проверить регом
    e = "/api/users"  # todo + проверить админом!!!

    # todo сделай красиво в цикле по словарю как было в спринте, постарайся!!!
    # routing = {
    #     INDEX: 'posts/index.html',
    #     CREATE: 'posts/create_post.html',
    #     GROUP_POSTS: 'posts/group_list.html',
    #     PROFILE: 'posts/profile.html',
    #     self.POST_DETAIL: 'posts/post_detail.html',
    #     self.POST_EDIT: 'posts/create_post.html'
    # }
    # for address, template in routing.items():
    #     with self.subTest(address=address):
    #         self.assertTemplateUsed(
    #             self.author.get(address), template
    #         )

    async with async_client as ac:
        # response = await ac.patch(api_url, json=data_patch)
        response_get_users_me = await ac.get(users_me_url)  # GET "/api/users/me"
        response_patch_users_me = await ac.patch(users_me_url, json=data_patch)  # PATCH "/api/users/me"
        response_get_test_url = await ac.get(  # GET "/api/services/test_url"
            test_url, params={"url": "https://agidel-am.ru/"}
        )
        response_db_backups = await ac.get(db_backups_url)  # GET "/api/services/db_backup"
        response_post_login = await ac.post(login_url, data=login_data)  # POST "/api/auth/jwt/login"
        response_post_logout = await ac.post(logout_url,)  # POST "/api/auth/jwt/logout"

    assert response_get_users_me.status_code == 401, f"Unauthorized get {users_me_url} but shouldn't"
    await log.ainfo("get_users_me", response=response_get_users_me.json(), url=response_get_users_me.url,
                    status_code=response_get_users_me.status_code)

    assert response_patch_users_me.status_code == 401, f"Unauthorized patch {users_me_url} but shouldn't"
    await log.ainfo("patch_users_me", response=response_patch_users_me.json(), url=response_patch_users_me.url,
                    status_code=response_patch_users_me.status_code)

    assert response_get_test_url.status_code == 200, f"Unauthorized couldn't get {test_url} but should"
    await log.ainfo("get_test_url", response=response_get_test_url.json(), url=response_get_test_url.url,
                    status_code=response_get_test_url.status_code)

    assert response_db_backups.status_code == 401, f"Unauthorized get {db_backups_url} but shouldn't"
    await log.ainfo("get_db_backups", response=response_db_backups.json(), url=response_db_backups.url,
                    status_code=response_db_backups.status_code)

    assert response_post_login.status_code == 400, f"Unauthorized post {login_url} but shouldn't"
    await log.ainfo("post_login", response=response_post_login.json(), url=response_post_login.url,
                    status_code=response_post_login.status_code)

    assert response_post_logout.status_code == 401, f"Unauthorized post {logout_url} but shouldn't"
    await log.ainfo("post_logout", response=response_post_logout.json(), url=response_post_logout.url,
                    status_code=response_post_logout.status_code)


async def test_user_create_login_and_logout(async_client: AsyncClient, async_db: AsyncSession) -> None:
    """
    Тестирует эндпоинт регистрации пользователей, логин и логаут:
    pytest -k test_user_create_login_and_logout -vs
    """
    register_url = "/api/auth/register"
    login_url = "/api/auth/jwt/login"
    logout_url = "/api/auth/jwt/logout"
    email = "test_create_user@nofoobar.com"
    password = "testing_testing"
    register_data = {"email": email, "password": password, "is_superuser": True}
    login_data = {"username": email, "password": password}
    async with async_client as ac:
        response_register = await ac.post(register_url, json=register_data)  # POST "/api/auth/register"
        response_post_login = await ac.post(login_url, data=login_data)  # POST "/api/auth/jwt/login"
        response_post_logout = await ac.post(  # POST "/api/auth/jwt/logout"
            logout_url,
            headers={"Authorization": f"Bearer {response_post_login.json()['access_token']}"}
        )

    assert response_register.status_code == 201, (
        f"api: user register status code {response_register.status_code} is not 201"
    )
    user_created = await async_db.scalar(select(User).where(User.email == email))
    assert email == user_created.email, f"created user {user_created.email} doesn't meet expectations: {email}"
    assert response_register.json()["id"] == user_created.id, (
        f"user id {user_created.id} doesn't meet {response_register.json()['id']}"
    )
    assert response_register.json()["is_superuser"] == user_created.is_superuser, (
        "user is_superuser doesn't meet expectations"
    )
    assert user_created.is_superuser is False, f"user_created.is_superuser: {user_created.is_superuser} is not False"
    await log.ainfo(
        "post_auth_register:", response=response_register.json(), url=response_register.url,
        user_email=user_created.email, user_id=user_created.id, super_user=user_created.is_superuser,
    )

    assert response_post_login.status_code == 200, f"Just registered user: {login_data} couldn't get {login_url}"
    await log.ainfo("post_login", response=response_post_login.json(), url=response_post_login.url,
                    status_code=response_post_login.status_code, login_data=login_data)

    assert response_post_logout.status_code == 204, f"Just registered user: {login_data} couldn't get {logout_url}"
    await log.ainfo("post_logout", response=response_post_logout, url=response_post_logout.url,
                    status_code=response_post_logout.status_code)

async def test_user_and_super_user_exist(
        async_client: AsyncClient, async_db: AsyncSession, super_user_orm: User, user_orm: User
) -> None:
    """
    Тестирует, что в БД созданы супер-пользователь и пользователь.
    pytest -k test_user_and_super_user_exist -vs
    """
    super_user_orm_email = "super_user_fixture@nofoobar.com"
    user_orm_email = "user_fixture@nofoobar.com"
    assert super_user_orm.is_superuser is True, "super_user_orm is not super_user but should"
    assert super_user_orm.email == super_user_orm_email, (
        f"super_user_orm email: {super_user_orm_email} doesn't meet expectations: {super_user_orm_email}"
    )
    assert user_orm.is_superuser is False, "user_orm is super_user but shouldn't"
    assert user_orm.email == user_orm_email, (
        f"user_orm email: {user_orm.email} doesn't meet expectations: {user_orm_email}"
    )
    await log.ainfo(
        "test_info:",
        super_user_email=super_user_orm.email,
        super_user_id=super_user_orm.id,
        is_super_user_superuser=super_user_orm.is_superuser,
        user_email=user_orm.email,
        user_id=user_orm.id,
        is_user_superuser=user_orm.is_superuser
    )


async def test_authorized_patch_users_me(async_client: AsyncClient, async_db: AsyncSession) -> None:
    """
    Тестирует эндпоинт патча пользователя: __/api/users/me__
    pytest -k test_authorized_patch_users_me -vs
    """
    data = {"email": "testuser@nofoobar.com", "password": "testing_testing"}
    api_url = "/api/users/me"
    async with async_client as ac:
        # response = await ac.patch(api_url, json=data)  # todo finish
        response = await ac.get(api_url)  # todo finish
    assert response.status_code == 401
    await log.ainfo("patch_users_me", response=response.json(), url=response.url)


# def test_authorized_get_db_backup(async_client: AsyncClient):  # todo нужен авторизованный пользователь
#     """Тестирует сервисный эндпоинт бэкапа БД авторизованным пользователем: __/api/services/db_backup__"""
#     api_url = "/api/services/db_backup"
#     # response = client.get(api_url)
#     async with async_client as ac:
#         response = await ac.get(api_url)
#     # assert response.status_code == 200
