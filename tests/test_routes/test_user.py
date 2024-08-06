"""
Асинхронных тесты сервисных эндпоинтов и работы с пользователями: tests/test_routes/test_2.py
pytest -s -W ignore::DeprecationWarning
pytest -k test_unauthorized_get_urls -vs
pytest -vs
https://anyio.readthedocs.io/en/stable/testing.html
"""

import json
import pytest
import structlog
from httpx import AsyncClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger().bind(file_name=__file__)

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.db.models import User
from src.settings import settings
from tests.conftest import remove_all

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
async def test_unauthorized_get_urls(async_client: AsyncClient) -> None:
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
    get_users_id_url = "/api/users/{id}"
    patch_users_id_url = "/api/users/{id}"
    patch_users_me_url = "/api/users/me"
    get_api_users_url = "/api/users"

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
        response_post_logout = await ac.post(logout_url)  # POST "/api/auth/jwt/logout"
        response_get_users_id_url = await ac.get(get_users_id_url)  # GET "/api/users/{id}"
        response_patch_users_id_url = await ac.patch(get_users_id_url)  # PATCH "/api/users/{id}"
        response_patch_users_me_url = await ac.patch(patch_users_me_url)  # PATCH "/api/users/me"
        response_get_api_users_url = await ac.get(get_api_users_url)  # GET "/api/users"

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

    assert response_get_users_id_url.status_code == 401, f"Unauthorized get {get_users_id_url} but shouldn't"
    await log.ainfo("get_users_id", response=response_get_users_id_url.json(), url=get_users_id_url,
                    status_code=response_get_users_id_url.status_code)

    assert response_patch_users_id_url.status_code == 401, f"Unauthorized get {patch_users_id_url} but shouldn't"
    await log.ainfo("patch_users_id", response=response_patch_users_id_url.json(), url=patch_users_id_url,
                    status_code=response_patch_users_id_url.status_code)

    assert response_patch_users_me_url.status_code == 401, f"Unauthorized get {patch_users_me_url} but shouldn't"
    await log.ainfo("patch_users_me", response=response_patch_users_me_url.json(), url=patch_users_me_url,
                    status_code=response_patch_users_me_url.status_code)

    assert response_get_api_users_url.status_code == 401, f"Unauthorized get {get_api_users_url} but shouldn't"
    await log.ainfo("get_api_users", response=response_get_api_users_url.json(), url=get_api_users_url,
                    status_code=response_get_api_users_url.status_code)

# todo refactorings!!!
# + todo тесты на разные парольные политики
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
        response_post_logout = await ac.post(
            logout_url,  # POST "/api/auth/jwt/logout"
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


async def test_super_user_get_users_id(
        async_client: AsyncClient,
        async_db: AsyncSession,
        super_user_orm: User,
        user_orm: User,
) -> None:
    """
    Тестирует эндпоинт получения информации о пользователе: __/api/users/{id}__
    pytest -k test_super_user_get_users_id -vs
    """
    login_data = {"username": "super_user_fixture@f.com", "password": "testings"}
    login_url = "/api/auth/jwt/login"
    users_id_url = f"/api/users/{user_orm.id}"
    async with async_client as ac:
        response_login_user = await ac.post(login_url, data={"username": "user_fixture@f.com", "password": "testings"})
        response_users_id_by_user = await ac.get(
            users_id_url,  # POST "/api/users/{id}"
            headers={"Authorization": f"Bearer {response_login_user.json()['access_token']}"},
        )
        response_login_super_user = await ac.post(login_url, data=login_data)
        response_users_id = await ac.get(
            users_id_url,
            headers={"Authorization": f"Bearer {response_login_super_user.json()['access_token']}"},
        )
    assert response_users_id_by_user.status_code == 403, f"User: {user_orm.email} get {users_id_url} but mustn't"
    await log.ainfo("post_users_id_by_user", response=response_users_id_by_user.json(), user=user_orm.email,
                    url=response_users_id_by_user.url, status_code=response_users_id_by_user.status_code)

    assert response_users_id.status_code == 200, f"Super_user: {login_data} couldn't get {users_id_url}"
    assert response_users_id.json()["id"] == user_orm.id, (
        f"Requested users id: {user_orm.id} doesn't match response {response_users_id.json()['id']}"
    )
    assert response_users_id.json()["email"] == user_orm.email, (
        f"Requested users email: {user_orm.email} doesn't match response {response_users_id.json()['email']}"
    )
    users_ids_after_remove = await remove_all(async_db, User)  # delete all to clean the database and isolate tests
    assert users_ids_after_remove == [], f"Users haven't been deleted: {users_ids_after_remove}"
    await log.ainfo("post_users_id_by_super_user", response=response_users_id.json(), url=response_users_id.url,
                    status_code=response_users_id.status_code, login_data=login_data,
                    users_ids_after_remove=users_ids_after_remove)


async def test_super_user_patch_users_id(
        async_client: AsyncClient,
        async_db: AsyncSession,
        super_user_orm: User,
        user_orm: User,
) -> None:
    """
    Тестирует эндпоинт редактирования информации о пользователе: __/api/users/{id}__
    pytest -k test_super_user_patch_users_id -vs
    """
    login_data = {"username": "super_user_fixture@f.com", "password": "testings"}
    login_edited_data = {"username": "user_edited@f.com", "password": "testings_edited"}
    edited_user_data = {"email": "user_edited@f.com", "password": "testings_edited"}
    login_url = "/api/auth/jwt/login"
    users_id_url = f"/api/users/{user_orm.id}"
    async with async_client as ac:
        response_login_user = await ac.post(login_url, data={"username": "user_fixture@f.com", "password": "testings"})
        response_patch_users_id_by_user = await ac.patch(
            users_id_url,  # POST "/api/users/{id}"
            json=edited_user_data,
            headers={"Authorization": f"Bearer {response_login_user.json()['access_token']}"},
        )
        response_login_super_user = await ac.post(login_url, data=login_data)
        response = await ac.patch(
            users_id_url,
            json=edited_user_data,
            headers={"Authorization": f"Bearer {response_login_super_user.json()['access_token']}"},
        )
        response_login_edited_user = await ac.post(login_url, data=login_edited_data)
    assert response_patch_users_id_by_user.status_code == 403, f"User: {user_orm.email} get {users_id_url} but mustn't"
    await log.ainfo("patch_users_id_by_user", response=response_patch_users_id_by_user.json(), user=user_orm.email,
                    url=response_patch_users_id_by_user.url, status_code=response_patch_users_id_by_user.status_code)

    assert response_login_edited_user.status_code == 200, f"Edited User: {login_edited_data} couldn't login"

    assert response.status_code == 200, f"Super_user: {login_data} couldn't get {users_id_url}"
    assert response.json()["id"] == user_orm.id, (
        f"Requested users id: {user_orm.id} doesn't match response {response.json()['id']}"
    )
    assert response.json()["email"] == edited_user_data["email"], (
        f"Edited users email: {edited_user_data['email']} doesn't match response {response.json()['email']}"
    )
    users_ids_after_remove = await remove_all(async_db, User)  # delete all to clean the database and isolate tests
    assert users_ids_after_remove == [], f"Users haven't been deleted: {users_ids_after_remove}"

    await log.ainfo("patch_users_id_by_user", response=response.json(), url=response.url, edited_data=edited_user_data,
                    status_code=response.status_code, login_data=login_data, new_email=response.json()["email"],
                    id=response.json()["id"], users_ids_after_remove=users_ids_after_remove)


async def test_user_patch_users_me(async_client: AsyncClient, async_db: AsyncSession, user_orm: User) -> None:
    """
    Тестирует эндпоинт патча пользователя: __/api/users/me__
    pytest -k test_user_patch_users_me -vs
    """
    login_data = {"username": "user_fixture@f.com", "password": "testings"}
    edited_user_data = {"email": "user_edited@f.com", "password": "testings_edited"}
    login_edited_data = {"username": "user_edited@f.com", "password": "testings_edited"}
    login_url = "/api/auth/jwt/login"
    users_me_url = f"/api/users/me"
    async with async_client as ac:
        response_login_user = await ac.post(login_url, data=login_data)
        response = await ac.patch(
            users_me_url,  # POST "/api/users/me"
            json=edited_user_data,
            headers={"Authorization": f"Bearer {response_login_user.json()['access_token']}"},
        )
        response_login_edited_user = await ac.post(login_url, data=login_edited_data)
    assert response.status_code == 200, f"User: {login_data} couldn't get {users_me_url}"
    assert edited_user_data["email"] == response.json()["email"], (
        f"Edited user's email: {response.json()['email']} doesn't meet expectations: {edited_user_data['email']}"
    )
    assert response_login_edited_user.status_code == 200, f"Edited User: {login_edited_data} couldn't login"
    users_ids_after_remove = await remove_all(async_db, User)  # delete all to clean the database and isolate tests
    assert users_ids_after_remove == [], f"Users haven't been deleted: {users_ids_after_remove}"
    await log.ainfo("patch_users_me_by_user", response=response.json(), url=response.url, edited_data=edited_user_data,
                    status_code=response.status_code, login_data=login_data, new_email=response.json()["email"],
                    id=response.json()["id"], users_ids_after_remove=users_ids_after_remove)


async def test_super_user_get_api_users(
        async_client: AsyncClient,
        async_db: AsyncSession,
        super_user_orm: User,
        user_orm: User,
) -> None:
    """
    Тестирует эндпоинт получения информации админом об активных пользователях: __/api/users__
    pytest -k test_super_user_get_api_users -vs
    """
    login_data = {"username": "super_user_fixture@f.com", "password": "testings"}
    login_url = "/api/auth/jwt/login"
    api_users_url = "/api/users"
    async with async_client as ac:
        response_login_user = await ac.post(login_url, data={"username": "user_fixture@f.com", "password": "testings"})
        response_api_users_by_user = await ac.get(
            api_users_url,  # GET "/api/users"
            headers={"Authorization": f"Bearer {response_login_user.json()['access_token']}"},
        )
        response_login_super_user = await ac.post(login_url, data=login_data)
        response_api_users = await ac.get(
            api_users_url,
            headers={"Authorization": f"Bearer {response_login_super_user.json()['access_token']}"},
        )
    super_user_email_response = json.loads(response_api_users.json())[f"{super_user_orm.id}"]
    user_email_response = json.loads(response_api_users.json())[f"{user_orm.id}"]

    assert response_api_users_by_user.status_code == 403, f"User: {user_orm.email} get {api_users_url} but mustn't"
    await log.ainfo("get_api_users_by_user", response=response_api_users_by_user.json(), user=user_orm.email,
                    url=response_api_users_by_user.url, status_code=response_api_users_by_user.status_code)

    assert response_api_users.status_code == 200, f"Super_user: {login_data} couldn't get {api_users_url}"

    assert super_user_email_response == super_user_orm.email, (
        f"Super_user response email: {super_user_email_response} doesn't match expectations {super_user_orm.email}"
    )
    assert user_email_response == user_orm.email, (
        f"User response email: {user_email_response} doesn't match expectations {user_orm.email}"
    )

    users_ids_after_remove = await remove_all(async_db, User)  # delete all to clean the database and isolate tests
    assert users_ids_after_remove == [], f"Users haven't been deleted: {users_ids_after_remove}"
    await log.ainfo("get_api_users_by_super_user", response=response_api_users.json(), url=response_api_users.url,
                    status_code=response_api_users.status_code, login_data=login_data,
                    users_ids_after_remove=users_ids_after_remove)


# def test_authorized_get_db_backup(async_client: AsyncClient):  # todo нужен авторизованный пользователь
#     """Тестирует сервисный эндпоинт бэкапа БД авторизованным пользователем: __/api/services/db_backup__"""
#     api_url = "/api/services/db_backup"
#     # response = client.get(api_url)
#     async with async_client as ac:
#         response = await ac.get(api_url)
#     # assert response.status_code == 200
