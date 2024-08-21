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
from src.settings import settings

from tests.conftest import remove_all

# cf = structlog.testing.CapturingLoggerFactory()  # https://www.structlog.org/en/stable/testing.html
# structlog.configure(logger_factory=cf, processors=[structlog.processors.JSONRenderer()])
# log = get_logger()
# cf.logger.calls

log = structlog.get_logger() if settings.FILE_NAME_IN_LOG is False else structlog.get_logger().bind(file_name=__file__)
# log = structlog.stdlib.get_logger("api.access")
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
        # user_from_settings: User,
        suspensions_orm: Suspension
) -> None:
    """
    Тестирует доступ пользователя к эндпоинту аналитики:
    pytest -k test_user_get_suspension_analytics_url -vs
    """
    login_url = "/api/auth/jwt/login"
    test_url = SUSPENSIONS_PATH+ANALYTICS  # /api/suspensions/analytics
    user_settings_email = json.loads(settings.STAFF)['1']
    user_settings_login = {"username": user_settings_email, "password": "testings"}
    user_orm_login = {"username": "user_fixture@f.com", "password": "testings"}
    now = datetime.now(TZINFO).strftime(DATE_TIME_FORMAT)
    day_ago = (datetime.now(TZINFO) - timedelta(days=1)).strftime(DATE_TIME_FORMAT)
    scenario_number = 0
    search_scenarios = (
        # login, params, status, count, minutes, measures, users_ids   # todo
        (user_settings_login, {ANALYTICS_START: day_ago, ANALYTICS_FINISH: now}, 200, 2, 70, ["3", "4"], [1, 2]),
        (user_orm_login, {ANALYTICS_START: day_ago, ANALYTICS_FINISH: now, USER_MAIL: user_settings_email}, 200,
         1, 10, ["3"], [1]),
    )
    # ({"username": user_settings_email, "password": "testings"}, {ANALYTICS_START: day_ago, ANALYTICS_FINISH: now})
    # ({ANALYTICS_START: day_ago, ANALYTICS_FINISH: now}, 200)

    async with async_client as ac:
        for login, search_params, status, count, minutes, measures, ids_users in search_scenarios:  # todo
            response_login_user = await ac.post(login_url, data=login)
            response = await ac.get(
                test_url,
                params=search_params,
                headers={"Authorization": f"Bearer {response_login_user.json()['access_token']}"},
            )
            suspensions_list = response.json()['Список всех случаев простоя.']
            total_suspensions = len(suspensions_list)
            total_minutes = response.json()['Сумма простоев в периоде (мин.)']
            implementing_measures = []
            users_ids = []
            [implementing_measures.append(suspension["Предпринятые действия"]) for suspension in suspensions_list]
            [users_ids.append(suspension["id пользователя"]) for suspension in suspensions_list]
            assert response.status_code == status, f"User: {login} couldn't get {test_url}"
            assert total_suspensions == count, (
                f"Suspensions_total: {total_suspensions} doesn't match expectations: {count}"
            )
            assert total_minutes == minutes, (
                f"Suspensions_in_mins_total: {total_minutes} doesn't match expectations: {minutes}"
            )
            assert set(implementing_measures) == set(measures), (
                f"Implementing_measures_(==ids): {implementing_measures} don't match expectations: {measures}"
            )
            assert set(users_ids) == set(ids_users), f"Users_ids: {users_ids} don't match expectations: {ids_users}"
            scenario_number += 1
            await log.ainfo(
                f"scenario_number: {scenario_number} ",
                login_data=login,
                params=search_params,
                suspensions_in_mins_total=total_minutes,
                suspensions_total=response.json()['Количество простоев в периоде'],
                measures=implementing_measures,
                users_ids=users_ids,
                suspensions_list=suspensions_list
            )

    # search_params = {
    #     ANALYTICS_START: day_ago,
    #     # ANALYTICS_FINISH: (datetime.now(TZINFO) + timedelta(days=1)).strftime(DATE_TIME_FORMAT),
    #     ANALYTICS_FINISH: now,
    #     # USER_MAIL: user_settings_email
    # }

    # await log.ainfo("suspension_orm", suspension_start=suspension_orm.suspension_start)
    # async with async_client as ac:
    #     response_login_user = await ac.post(login_url, data=login_data)
    #     response = await ac.get(
    #         test_url,
    #         params=search_params,
    #         headers={"Authorization": f"Bearer {response_login_user.json()['access_token']}"},
    #     )
    # assert response.status_code == 200, f"User: {login_data} couldn't get {test_url}"


# todo разные проверки тут!!!
    # Нужны 4 простоя для 4х сценариев и подсчет каждого сценария:  # todo
    # 1 до окна поиска начинается и заканчивается (1 мин),  # todo
    # 2 до окна поиска начинается и заканчивается в окне поиска (5 мин),  # todo
    # 3 в окне начинается и заканчивается (10 мин),  # todo
    # 4 начинается в окне и заканчивается за окном (60 мин), # todo
    # Проверить подсчет суммы в каждом из 4х сценариев  # todo
    # Левое окно запроса после начала простоя # todo
    # Правовое окно запроса до окончания простоя  # todo
    # Правое окно раньше левого  # todo
    # Левое окно позже правого  # todo
    # Леовое окно равно правому  # todo
    # Несуществующий id пользователя  # todo
    # Несуществующий email пользователя  # todo
    # Простои от разных пользователей - не должно быть простоев от чужих пользователей при включении фильтра # todo
    # Нарушение формата ввода данных  # todo
    #   # todo
    #   # todo
    #   # todo

    # assert edited_user_data["email"] == response.json()["email"], (
    #     f"Edited user's email: {response.json()['email']} doesn't meet expectations: {edited_user_data['email']}"
    # )
    # print(f'response: {response.json()}')
    # suspensions_list = response.json()['Список всех случаев простоя.']
    # await log.ainfo(
    #     "info: ",
    #     params=search_params,
    #     suspensions_in_mins_total=response.json()['Сумма простоев в периоде (мин.)'],
    #     suspensions_total=response.json()['Количество простоев в периоде'],
    #     suspension_start=suspensions_list[0]['Начало простоя'] if suspensions_list != [] else [],
    #     suspension_finish=suspensions_list[0]['Окончание простоя'] if suspensions_list != [] else [],
    #     # suspension_risk_accident=suspensions_list[0]['Риск-инцидент'] if suspensions_list != [] else [],
    #     measures=suspensions_list[0]['Предпринятые действия'] if suspensions_list != [] else [],
    # )

    users_ids_after_remove = await remove_all(async_db, User)  # delete all to clean the database and isolate tests
    assert users_ids_after_remove == [], f"Users haven't been deleted: {users_ids_after_remove}"
    suspensions_ids_after_remove = await remove_all(async_db, Suspension)  # delete all to clean the database
    assert suspensions_ids_after_remove == [], f"Suspensions haven't been deleted: {suspensions_ids_after_remove}"

    await log.ainfo("test_suspension_analytics", users_ids_after_remove=users_ids_after_remove,
                    suspensions_ids_after_remove=suspensions_ids_after_remove)


    # print(f"user_orm_email: {user_orm.email}")
    # print(f"user_from_settings: {json.loads(settings.STAFF)['1']}")
    # print(f"tech_process: {next(iter(json.loads(settings.TECH_PROCESS).values()))}")
    # print(f"risk_accident: {next(iter(json.loads(settings.RISK_SOURCE).values()))}")
    # print(f"tech_process: {settings.TECH_PROCESS.values()}")