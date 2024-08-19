"""
Асинхронных тесты сервисных эндпоинтов и работы с пользователями: tests/test_routes/test_user.py
pytest -s -W ignore::DeprecationWarning
pytest -k test_unauthorized_get_urls -vs
pytest -vs
https://anyio.readthedocs.io/en/stable/testing.html
"""
import json
import os
import sys
from datetime import date

import pytest
import structlog
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.core.db.models import User
from src.settings import settings
from tests.conftest import remove_all

log = structlog.get_logger() if settings.FILE_NAME_IN_LOG is False else structlog.get_logger().bind(file_name=__file__)
pytestmark = pytest.mark.anyio  # make all test mark with `anyio` or use decorator: # @pytest.mark.anyio


async def test_unauthorized_tries_service_and_auth_urls(async_client: AsyncClient) -> None:
    """
    Тестирует доступ к сервисным и аутентификационным апи неавторизованным пользователем:
    pytest -k test_unauthorized_tries_service_and_auth_urls -vs
    """
    get_params_urls = (
        ("/api/services/test_url", {"url": "https://agidel-am.ru/"}, 200),
        ("/api/users/me", {}, 401),
        ("/api/services/db_backup", {}, 401),
        ("/api/users/{id}", {}, 401),
        ("/api/users", {}, 401)
    )

    patch_json_urls = (
        ("/api/users/me", {"email": "testuser@nofoobar.com", "password": "testing_testing"}, 401),
        ("/api/users/me", {}, 401),
        ("/api/users/{id}", {}, 401),
    )

    post_data_urls = (
        ("/api/auth/jwt/login", {"username": "some_unknown@username.com", "password": "unknown_password"}, 400),
        ("/api/auth/jwt/logout", {}, 401),
    )

    async with async_client as ac:
        for api_url, params, status in get_params_urls:
            response = await ac.get(api_url, params=params)
            assert response.status_code == status, f"test_url: {api_url} with params: {params} is not {status}"
            await log.ainfo(
                "{}".format(api_url), response=response.json(), status=response.status_code, request=response._request
            )
        for api_url, json_data, status in patch_json_urls:
            response = await ac.patch(api_url, json=json_data)
            assert response.status_code == status, f"test_url: {api_url} with json_data: {json_data} is not {status}"
            await log.ainfo(
                "{}".format(api_url), json=json_data, response=response.json(), status=response.status_code,
                request=response._request,
            )
        for api_url, data, status in post_data_urls:
            response = await ac.post(api_url, data=data)
            assert response.status_code == status, f"test_url: {api_url} with data: {data} is not {status}"
            await log.ainfo(
                "{}".format(api_url), data=data, response=response.json(), status=response.status_code,
                request=response._request,
            )
            # print(f'response: {dir(response)}')


async def test_user_register_login_and_logout(async_client: AsyncClient, async_db: AsyncSession) -> None:
    """
    Тестирует эндпоинт регистрации пользователей и их последующего логин и логаут:
    pytest -k test_user_register_login_and_logout -vs
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

    assert response_register.status_code == 201, f"Unsuccessful register status code: {response_register.status_code}"

    user_created = await async_db.scalar(select(User).where(User.email == email))
    assert email == user_created.email, f"Created user {user_created.email} doesn't meet expectations: {email}"
    assert response_register.json()["id"] == user_created.id, (
        f"User's id {user_created.id} doesn't meet expectations: {response_register.json()['id']}"
    )
    assert response_register.json()["is_superuser"] == user_created.is_superuser, (
        f"User's status of super_user: {user_created.is_superuser} doesn't meet expectations: {False}"
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

    users_ids_after_remove = await remove_all(async_db, User)  # delete all to clean the database and isolate tests
    assert users_ids_after_remove == [], f"Users haven't been deleted: {users_ids_after_remove}"
    await log.ainfo("clean the database", users_ids_after_remove=users_ids_after_remove)


async def test_user_register_password_policy(async_client: AsyncClient, async_db: AsyncSession) -> None:
    """
    Тестирует эндпоинт регистрации пользователей и соблюдение требований политики парольной безопасности:
    pytest -k test_user_register_password_policy -vs
    """
    register_url = "/api/auth/register"
    email = "test_create_user@nofoobar.com"
    register_data_scenarios = (
        ({"email": email, "password": "testing_testing"}, 201),
        ({"email": email, "password": "test"}, 400),  # if len(password) < 6
        ({"email": email, "password": email}, 400)  # if user.email in password
    )
    async with async_client as ac:
        for register_data, status in register_data_scenarios:
            response = await ac.post(register_url, json=register_data)  # POST "/api/auth/register"
            assert response.status_code == status, (
                f"Status code: {response.status_code} doesn't match expectations: {status}"
            )
            # await log.ainfo("register user scenario:", register_data=register_data, response=response.json())
    users_ids_after_remove = await remove_all(async_db, User)  # delete all to clean the database and isolate tests
    assert users_ids_after_remove == [], f"Users haven't been deleted: {users_ids_after_remove}"
    await log.ainfo("clean the database", users_ids_after_remove=users_ids_after_remove)


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
    users_me_url = "/api/users/me"
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


async def test_super_user_get_db_backup(
        async_client: AsyncClient,
        async_db: AsyncSession,
        super_user_orm: User,
        user_orm: User,
) -> None:
    """
    Тестирует эндпоинт мануального бэкапа БД: __/api/services/db_backup__
    pytest -k test_super_user_get_db_backup -vs
    """
    login_data = {"username": "super_user_fixture@f.com", "password": "testings"}
    login_url = "/api/auth/jwt/login"
    db_backup_url = "/api/services/db_backup"
    async with async_client as ac:
        response_login_user = await ac.post(login_url, data={"username": "user_fixture@f.com", "password": "testings"})
        response_db_backup_by_user = await ac.get(
            db_backup_url,  # GET "/api/services/db_backup"
            headers={"Authorization": f"Bearer {response_login_user.json()['access_token']}"},
        )
        response_login_super_user = await ac.post(login_url, data=login_data)
        response_db_backup = await ac.get(
            db_backup_url,  # GET "/api/services/db_backup"
            headers={"Authorization": f"Bearer {response_login_super_user.json()['access_token']}"},
        )

    assert response_db_backup_by_user.status_code == 403, f"User: {user_orm.email} get {db_backup_url} but mustn't"
    await log.ainfo("get_api_users_by_user", response=response_db_backup_by_user.json(), user=user_orm.email,
                    url=response_db_backup_by_user.url, status_code=response_db_backup_by_user.status_code)

    assert response_db_backup.status_code == 200, f"Super_user: {login_data} couldn't get {db_backup_url}"

    assert response_db_backup.json()["total_backups"] > 0, (
        f"Total_backups: {response_db_backup.json()['total_backups']} should be positive int"
    )

    assert str(response_db_backup.json()["last_backup"]) == str(date.today()), (
        f"Last_backup: {response_db_backup.json()['last_backup']} should be today: {date.today()}"
    )

    users_ids_after_remove = await remove_all(async_db, User)  # delete all to clean the database and isolate tests
    assert users_ids_after_remove == [], f"Users haven't been deleted: {users_ids_after_remove}"
    await log.ainfo("get_api_users_by_super_user", response=response_db_backup.json(), url=response_db_backup.url,
                    status_code=response_db_backup.status_code, login_data=login_data,
                    users_ids_after_remove=users_ids_after_remove)
