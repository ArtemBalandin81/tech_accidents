"""
Асинхронные тесты работы эндпоинтов простоев: tests/test_routes/test_suspension.py
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
from src.api.constants import *
from src.api.endpoints import file_router, suspension_router
from src.core.db.models import User, Suspension

from tests.conftest import remove_all

log = structlog.get_logger().bind(file_name=__file__)
pytestmark = pytest.mark.anyio  # make all test mark with `anyio` or use decorator: # @pytest.mark.anyio

SUSPENSIONS_PATH = settings.ROOT_PATH + "/suspensions"  # /api/suspensions/

async def test_unauthorized_tries_suspension_urls(async_client: AsyncClient) -> None:
    """
    Тестирует доступ к эндпоинтам простоев неавторизованным пользователем:
    pytest -k test_unauthorized_tries_suspension_urls -vs
    """
    # print(f"suspension_router: {suspension_router.routes}")
    get_params_urls = (
        (SUSPENSIONS_PATH+ANALYTICS, {}, 401),  # /api/suspensions/analytics
        (SUSPENSIONS_PATH + MAIN_ROUTE, {}, 401),  # /api/suspensions/
        (SUSPENSIONS_PATH + MY_SUSPENSIONS, {}, 401),  # /api/my_suspensions/
        (SUSPENSIONS_PATH + SUSPENSION_ID, {}, 401),  # /api/suspensions/{suspension_id}
    )
    patch_data_urls = (
        (SUSPENSIONS_PATH+SUSPENSION_ID, {}, 401),  # /api/suspensions/{suspension_id}
    )
    post_data_urls = (
        (SUSPENSIONS_PATH+POST_SUSPENSION_FORM, {}, 401),  # /api/suspensions/post_suspension_form
        (SUSPENSIONS_PATH + POST_SUSPENSION_FILES_FORM, {}, 401),  # /api/suspensions/post_suspension_with_files_form
        (SUSPENSIONS_PATH + ADD_FILES_TO_SUSPENSION, {}, 401),  # /api/suspensions/add_files_to_suspension
    )

    async with async_client as ac:
        for api_url, params, status in get_params_urls:
            response = await ac.get(api_url, params=params)
            assert response.status_code == status, f"test_url: {api_url} with params: {params} is not {status}"
            await log.ainfo(
                "{}".format(api_url), response=response.json(), status=response.status_code, request=response._request
            )
        for api_url, data, status in patch_data_urls:
            response = await ac.patch(api_url, data=data)
            assert response.status_code == status, f"test_url: {api_url} with data: {data} is not {status}"
            await log.ainfo(
                "{}".format(api_url), data=data, response=response.json(), status=response.status_code,
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

async def test_user_get_suspension_analytics_url(
        async_client: AsyncClient,
        async_db: AsyncSession,
        user_from_settings: User,
        suspension_orm: Suspension
) -> None:
    """
    Тестирует доступ пользователя к эндпоинту аналитики:
    pytest -k test_user_get_suspension_analytics_url -vs
    """
    login_url = "/api/auth/jwt/login"
    test_url = SUSPENSIONS_PATH+ANALYTICS  # /api/suspensions/analytics
    user_settings_email = json.loads(settings.STAFF)['1']
    login_data = {"username": user_settings_email, "password": "testings"}
    params = {ANALYTICS_START: ANALYTIC_FROM_TIME, ANALYTICS_FINISH: ANALYTIC_TO_TIME, USER_MAIL: user_settings_email}

    # await log.ainfo("suspension_orm", suspension_start=suspension_orm.suspension_start)
    async with async_client as ac:
        response_login_user = await ac.post(login_url, data=login_data)
        response = await ac.get(
            test_url,
            params=params,
            headers={"Authorization": f"Bearer {response_login_user.json()['access_token']}"},
        )

# todo разные проверки тут!!!
    assert response.status_code == 200, f"User: {login_data} couldn't get {test_url}"
    # assert edited_user_data["email"] == response.json()["email"], (
    #     f"Edited user's email: {response.json()['email']} doesn't meet expectations: {edited_user_data['email']}"
    # )


    users_ids_after_remove = await remove_all(async_db, User)  # delete all to clean the database and isolate tests
    assert users_ids_after_remove == [], f"Users haven't been deleted: {users_ids_after_remove}"
    suspensions_ids_after_remove = await remove_all(async_db, Suspension)  # delete all to clean the database
    assert suspensions_ids_after_remove == [], f"Suspensions haven't been deleted: {suspensions_ids_after_remove}"

    await log.ainfo("get_suspension_analytics", response=response.json(), url=response.url, login_data=login_data,
                    status_code=response.status_code, users_ids_after_remove=users_ids_after_remove,
                    suspensions_ids_after_remove=suspensions_ids_after_remove)


    # print(f"user_orm_email: {user_orm.email}")
    # print(f"user_from_settings: {json.loads(settings.STAFF)['1']}")
    # print(f"tech_process: {next(iter(json.loads(settings.TECH_PROCESS).values()))}")
    # print(f"risk_accident: {next(iter(json.loads(settings.RISK_SOURCE).values()))}")
    # print(f"tech_process: {settings.TECH_PROCESS.values()}")