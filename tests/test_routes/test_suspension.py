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
from pathlib import Path
import pytest
import structlog
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.api.constants import *
from src.api.endpoints import file_router, suspension_router
from src.core.db.models import FileAttached, User, Suspension
from src.core.enums import TechProcess
from src.settings import settings

from tests.conftest import delete_files_in_folder, get_files_for_model_db, remove_all


log = structlog.get_logger() if settings.FILE_NAME_IN_LOG is False else structlog.get_logger().bind(file_name=__file__)
pytestmark = pytest.mark.anyio  # make all test mark with `anyio` or use decorator: # @pytest.mark.anyio

SUSPENSIONS_PATH = settings.ROOT_PATH + "/suspensions"  # /api/suspensions/
FILES_PATH = settings.ROOT_PATH + "/files"  # /api/files/  # todo удалить / перенести

SERVICES_DIR = Path(__file__).resolve().parent.parent.parent
FILES_DIR = SERVICES_DIR.joinpath(settings.FILES_DOWNLOAD_DIR)
TEST_ROUTES_DIR = Path(__file__).resolve().parent  # todo


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
        suspensions_orm: Suspension
) -> None:
    """
    Тестирует доступ пользователя к эндпоинту аналитики:
    pytest -k test_user_get_suspension_analytics_url -vs
    """
    login_url = "/api/auth/jwt/login"
    test_url = SUSPENSIONS_PATH+ANALYTICS  # /api/suspensions/analytics
    user_settings_email = json.loads(settings.STAFF)["1"]
    user_settings_login = {"username": user_settings_email, "password": "testings"}
    user_orm_login = {"username": "user_fixture@f.com", "password": "testings"}
    now = datetime.now(TZINFO).strftime(DATE_TIME_FORMAT)
    day_ago = (datetime.now(TZINFO) - timedelta(days=1)).strftime(DATE_TIME_FORMAT)
    two_days_ago = (datetime.now(TZINFO) - timedelta(days=2)).strftime(DATE_TIME_FORMAT)
    future_1_day = (datetime.now(TZINFO) + timedelta(days=1)).strftime(DATE_TIME_FORMAT)
    last_time_suspension_expected = (datetime.now() - timedelta(minutes=15)).strftime(DATE_TIME_FORMAT)
    error_in_date = "11-07-20244: 18:45"
    error_in_time = "11-07-2024: 45:18"
    # we need to correct last_time_suspension_expected for 1 min in ANALYTICS_FINISH because of time tests running:
    last_time_suspension_exp_corrections = (datetime.now() - timedelta(minutes=14)).strftime(DATE_TIME_FORMAT)
    scenario_number = 0
    search_scenarios = (
        # login, params, status, count, minutes, measures, users_ids
        (user_settings_login, {ANALYTICS_START: day_ago, ANALYTICS_FINISH: now}, 200, 2, 70, ["3", "4"], [1, 2]),  # 1
        (user_orm_login, {ANALYTICS_START: day_ago, ANALYTICS_FINISH: now, USER_MAIL: user_settings_email}, 200,
         1, 10, ["3"], [1]),  # 2 filter by user_settings_email
        (user_orm_login, {ANALYTICS_START: now, ANALYTICS_FINISH: future_1_day}, 200, 0, 0, [], []),  # 3
        (user_orm_login, {ANALYTICS_START: last_time_suspension_expected, ANALYTICS_FINISH: future_1_day}, 200,
         1, 10, ["3"], [1]),  # 4
        (user_orm_login, {ANALYTICS_START: two_days_ago, ANALYTICS_FINISH: now}, 200,
         4, 2946, ["1", "2", "3", "4"], [1, 2]),  # 5  test all suspensions: 2946 mins and 4 suspensions
        (user_orm_login, {ANALYTICS_START: two_days_ago, ANALYTICS_FINISH: last_time_suspension_expected}, 200,
         3, 2936, ["1", "2", "4"], [1, 2]),  # 6  problem is in seconds: don't include last_time_suspension
        (user_orm_login, {ANALYTICS_START: two_days_ago, ANALYTICS_FINISH: last_time_suspension_exp_corrections}, 200,
         4, 2946, ["1", "2", "3", "4"], [1, 2]),  # 7  corrects the 6th scenario for time needed for tests running
        (user_orm_login, {ANALYTICS_START: now, ANALYTICS_FINISH: now}, 200, 0, 0, [], []),  # 8
        (user_orm_login, {ANALYTICS_START: now, ANALYTICS_FINISH: day_ago}, 422, None, None, [], []),  # 9 left>right
        (user_orm_login, {ANALYTICS_START: day_ago, ANALYTICS_FINISH: now, USER_MAIL: "unknown_user@f.com"}, 422,
         None, None, [], []),  # 10 filter by unknown_user
        (user_orm_login, {ANALYTICS_START: error_in_date, ANALYTICS_FINISH: now}, 422, None, None, [], []),  # 11 regex
        (user_orm_login, {ANALYTICS_START: error_in_time, ANALYTICS_FINISH: now}, 422, None, None, [], []),  # 12 regex
    )
    async with async_client as ac:
        for login, search_params, status, count, minutes, measures, ids_users in search_scenarios:
            response_login_user = await ac.post(login_url, data=login)
            response = await ac.get(
                test_url,
                params=search_params,
                headers={"Authorization": f"Bearer {response_login_user.json()['access_token']}"},
            )
            suspensions_list = response.json().get(SUSPENSION_LIST)
            total_suspensions = len(suspensions_list) if suspensions_list is not None else None
            total_minutes = response.json().get(MINS_TOTAL)
            last_time_suspension_id = response.json().get(SUSPENSION_LAST_ID)
            last_time_suspension = (
                response.json().get(SUSPENSION_LAST_TIME)
                if suspensions_list is not None else last_time_suspension_expected
            )
            implementing_measures = []
            users_ids = []
            last_time_suspension_id_expected = None
            if suspensions_list is not None:
                [implementing_measures.append(suspension[IMPLEMENTING_MEASURES]) for suspension in suspensions_list]
                [users_ids.append(suspension[USER_ID]) for suspension in suspensions_list]
                last_time_suspension_id_expected = 3  # Now it's = 3 - !!! FRANGIBLE depends on suspensions_orm
            assert response.status_code == status, f"User: {login} couldn't get {test_url}"
            assert total_suspensions == count, (
                f"Suspensions_total: {total_suspensions} doesn't match expectations: {count}"
            )
            assert total_minutes == minutes, (
                f"Suspensions_in_mins_total: {total_minutes} doesn't match expectations: {minutes}"
            )
            assert set(implementing_measures) == set(measures), (
                f"Implementing_measures_(means ids): {implementing_measures} don't match expectations: {measures}"
            )
            assert set(users_ids) == set(ids_users), f"Users_ids: {users_ids} don't match expectations: {ids_users}"
            assert last_time_suspension_id == last_time_suspension_id_expected, (
                f"Last  stimeuspension id: {last_time_suspension_id} is not: {last_time_suspension_id_expected}"
            )
            assert last_time_suspension == last_time_suspension_expected, (
                f"Last time suspension: {last_time_suspension} doesn't match: {last_time_suspension_expected}"
            )
            scenario_number += 1
            await log.ainfo(
                f"scenario_number: {scenario_number} ",
                login_data=login,
                params=search_params,
                status=response.status_code,
                suspensions_in_mins_total=total_minutes,
                suspensions_total=response.json().get(SUSPENSION_TOTAl),
                last_time_suspension_id=last_time_suspension_id,
                last_time_suspension=last_time_suspension,
                measures=implementing_measures,
                users_ids=users_ids,
                suspensions_list=suspensions_list
            )
    users_ids_after_remove = await remove_all(async_db, User)  # delete all to clean the database and isolate tests
    assert users_ids_after_remove == [], f"Users haven't been deleted: {users_ids_after_remove}"
    suspensions_ids_after_remove = await remove_all(async_db, Suspension)  # delete all to clean the database
    assert suspensions_ids_after_remove == [], f"Suspensions haven't been deleted: {suspensions_ids_after_remove}"
    await log.ainfo("test_suspension_analytics", users_ids_after_remove=users_ids_after_remove,
                    suspensions_ids_after_remove=suspensions_ids_after_remove)


async def test_user_post_suspension_form_url(
        async_client: AsyncClient,
        async_db: AsyncSession,
        user_orm: User,
        # suspensions_orm: Suspension
) -> None:
    """
    Тестирует фиксацию случая простоя из формы с возможностью загрузки 1 файла:
    pytest -k test_user_post_suspension_form_url -vs
    """
    login_url = "/api/auth/jwt/login"
    test_url = SUSPENSIONS_PATH+POST_SUSPENSION_FORM  # /api/suspensions/post_suspension_form
    user_settings_email = json.loads(settings.STAFF)["1"]
    user_settings_login = {"username": user_settings_email, "password": "testings"}
    user_orm_email = "user_fixture@f.com"
    user_orm_login = {"username": user_orm_email, "password": "testings"}
    now = datetime.now(TZINFO).strftime(DATE_TIME_FORMAT)
    day_ago = (datetime.now(TZINFO) - timedelta(days=1)).strftime(DATE_TIME_FORMAT)
    last_time_suspension_expected = (datetime.now() - timedelta(minutes=15)).strftime(DATE_TIME_FORMAT)
    params = {
        ANALYTICS_START: day_ago,
        ANALYTICS_FINISH: now,
        RISK_ACCIDENT_SOURCE: json.loads(settings.RISK_SOURCE)["ANOTHER"],
        TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
        SUSPENSION_DESCRIPTION: "test_description",
        IMPLEMENTING_MEASURES: "test_measures",
    }
    scenario_number = 0
    search_scenarios = (
        # login, params, status,
        (user_orm_login, params, 200),
    )
    async with async_client as ac:
        for login, create_params, status in search_scenarios:
            response_login_user = await ac.post(login_url, data=login)
            response = await ac.post(
                test_url,
                params=create_params,
                headers={"Authorization": f"Bearer {response_login_user.json()['access_token']}"},
                # files={"file": open(TEST_ROUTES_DIR.joinpath("testfile.txt"), "wb")},  # TODO somehow!!!
            )
            suspensions = await async_db.scalars(select(Suspension))
            suspensions_list = suspensions.all()
            new_object = suspensions_list[0]
            total_suspensions = len(suspensions_list) if suspensions_list is not None else None
            total_suspensions_expected = 1
            files_attached = await get_files_for_model_db(async_db, Suspension, new_object.id)
            duration_db = new_object.suspension_finish - new_object.suspension_start
            duration_params = (
                    datetime.strptime(create_params[ANALYTICS_FINISH], DATE_TIME_FORMAT)
                    - datetime.strptime(create_params[ANALYTICS_START], DATE_TIME_FORMAT)
            )
            assert response.status_code == status, f"User: {login} couldn't get {test_url}"
            assert total_suspensions == total_suspensions_expected, (
                f"Total suspensions: {total_suspensions} are not as expected: {total_suspensions_expected}"
            )
            assert new_object.id == response.json().get("id"), (
                f"Suspension id: {new_object.id} is not as expected: {response.json().get('id')}"
            )
            assert new_object.user_id == response.json().get(USER_ID), (
                f"Suspension user_id: {new_object.user_id} is not as expected: {response.json().get(USER_ID)}"
            )
            assert new_object.suspension_start.strftime(DATE_TIME_FORMAT) == response.json().get(SUSPENSION_START), (
                f"Suspension start: {new_object.suspension_start.strftime(DATE_TIME_FORMAT)}"
                f" is not: {response.json().get(SUSPENSION_START)}"
            )
            assert new_object.suspension_finish.strftime(DATE_TIME_FORMAT) == response.json().get(SUSPENSION_FINISH), (
                f"Suspension finish: {new_object.suspension_finish.strftime(DATE_TIME_FORMAT)}"
                f" is not: {response.json().get(SUSPENSION_FINISH)}"
            )
            assert new_object.implementing_measures == response.json().get(IMPLEMENTING_MEASURES), (
                f"Measures: {new_object.implementing_measures} are not: {response.json().get(IMPLEMENTING_MEASURES)}"
            )
            assert files_attached == response.json().get(FILES_SET_TO), (
                f"Attached files: {files_attached} are not as expected: {response.json().get(FILES_SET_TO)}"
            )
            assert new_object.risk_accident == response.json().get(RISK_ACCIDENT), (
                f"Risk_accident: {new_object.risk_accident} is not as expected: {response.json().get(RISK_ACCIDENT)}"
            )
            assert TechProcess(str(new_object.tech_process)).name == response.json().get(TECH_PROCESS), (
                f"Tech_process: {TechProcess(str(new_object.tech_process)).name}"
                f" is not: {response.json().get(TECH_PROCESS)}"
            )
            assert duration_db == duration_params, f"Duration db: {duration_db} is not as expected: {duration_params}"

            scenario_number += 1


            # FILES_DIR = TESTS_DIR.joinpath(settings.FILES_DOWNLOAD_DIR)  # move to settings todo
            print(f'TEST_ROUTES_DIR: {TEST_ROUTES_DIR.joinpath("testfile.txt")}')
            await log.ainfo(
                f"scenario_number: {scenario_number} ",
                login_data=login,
                duration_db=duration_db,
                duration_params=duration_params,
                params=create_params,
                response=response.json()
            )
    users_ids_after_remove = await remove_all(async_db, User)  # delete all to clean the database and isolate tests
    assert users_ids_after_remove == [], f"Users haven't been deleted: {users_ids_after_remove}"
    suspensions_ids_after_remove = await remove_all(async_db, Suspension)  # delete all to clean the database
    assert suspensions_ids_after_remove == [], f"Suspensions haven't been deleted: {suspensions_ids_after_remove}"
    await log.ainfo("test_user_post_suspension_form_url", users_ids_after_remove=users_ids_after_remove,
                    suspensions_ids_after_remove=suspensions_ids_after_remove)





# TODO endpoints suspensions
ADD_FILES_TO_SUSPENSION = "/add_files_to_suspension"
# ANALYTICS = "/analytics"  # is done!
MY_SUSPENSIONS = "/my_suspensions"
# POST_SUSPENSION_FORM = "/post_suspension_form"  # todo now
POST_SUSPENSION_FILES_FORM = "/post_suspension_with_files_form"
SUSPENSION_ID = "/{suspension_id}"


async def test_user_post_download_files_url(
        async_client: AsyncClient,
        async_db: AsyncSession,
        super_user_orm: User,
        # suspensions_orm: Suspension
) -> None:
    """
    Тестирует возможность загрузки 1 файла:
    pytest -k test_user_post_download_files_url -vs
    """
    login_url = "/api/auth/jwt/login"
    test_url = FILES_PATH+DOWNLOAD_FILES  # /api/files/download_files
    super_user_orm_login = {"username": "super_user_fixture@f.com", "password": "testings"}
    scenario_number = 0
    async with async_client as ac:
        response_login_user = await ac.post(login_url, data=super_user_orm_login)
        assert response_login_user.status_code == 200, f"User: {super_user_orm_login} couldn't get {login_url}"
        response = await ac.post(
            test_url,
            # params=search_params,
            files={"files": open(TEST_ROUTES_DIR.joinpath("testfile.txt"), "rb")},  # TODO somehow!!!
            headers={"Authorization": f"Bearer {response_login_user.json()['access_token']}"},
        )
        assert response.status_code == 200, f"User: {super_user_orm_login} couldn't get {test_url}"
        objects = await async_db.scalars(select(FileAttached))
        files_in_db = objects.all()
        file_name_saved_in_folder = response.json().get(FILES_WRITTEN_DB)[0].get("Имя файла.")

        await log.ainfo(
            f"scenario_number: {scenario_number} ",
            login_data=super_user_orm_login,
            # params=search_params,
            status=response.status_code,
            response=response.json(),
            files_in_db=files_in_db,
            files_dir=FILES_DIR,
            # file_name=response.json().get(FILES_WRITTEN_DB)[0].get("Имя файла.")
        )

    # todo а файл-то называется по-другому, там в нем метка есть
    await delete_files_in_folder([FILES_DIR.joinpath(file_name_saved_in_folder)])
    users_ids_after_remove = await remove_all(async_db, User)  # delete all to clean the database and isolate tests
    assert users_ids_after_remove == [], f"Users haven't been deleted: {users_ids_after_remove}"
    files_ids_after_remove = await remove_all(async_db, FileAttached)  # delete all to clean the database
    assert files_ids_after_remove == [], f"Files haven't been deleted: {files_ids_after_remove}"
    await log.ainfo("test_suspension_analytics", users_ids_after_remove=users_ids_after_remove,
                    files_ids_after_remove=files_ids_after_remove, file_removed_in_folder=file_name_saved_in_folder)







# async def test_user_post_suspension_form_url(
#         async_client: AsyncClient,
#         async_db: AsyncSession,
#         user_orm: User,
        # suspensions_orm: Suspension
# ) -> None:
#     """
#     Тестирует фиксацию случая простоя из формы с возможностью загрузки 1 файла:
#     pytest -k test_user_post_suspension_form_url -vs
#     """
#     login_url = "/api/auth/jwt/login"
#     test_url = SUSPENSIONS_PATH+POST_SUSPENSION_FORM  # /api/suspensions/post_suspension_form
#     user_settings_email = json.loads(settings.STAFF)["1"]
#     user_settings_login = {"username": user_settings_email, "password": "testings"}
#     user_orm_login = {"username": "user_fixture@f.com", "password": "testings"}
#     now = datetime.now(TZINFO).strftime(DATE_TIME_FORMAT)
#     day_ago = (datetime.now(TZINFO) - timedelta(days=1)).strftime(DATE_TIME_FORMAT)
#     scenario_number = 0
#     search_scenarios = (
#         # login, params, status, count, minutes, measures, users_ids
#         (user_settings_login, {ANALYTICS_START: day_ago, ANALYTICS_FINISH: now}, 200, 2, 70, ["3", "4"], [1, 2]),  # 1
#     )
#     async with async_client as ac:
#         for login, search_params, status, count, minutes, measures, ids_users in search_scenarios:
#             response_login_user = await ac.post(login_url, data=login)
#             response = await ac.get(
#                 test_url,
#                 params=search_params,
#                 headers={"Authorization": f"Bearer {response_login_user.json()['access_token']}"},
#             )
#             assert response.status_code == status, f"User: {login} couldn't get {test_url}"
#
#             scenario_number += 1
#             await log.ainfo(
#                 f"scenario_number: {scenario_number} ",
#                 login_data=login,
#                 # params=search_params,
#                 # status=response.status_code,
#                 # suspensions_in_mins_total=total_minutes,
#                 # suspensions_total=response.json().get(SUSPENSION_TOTAl),
#                 # last_time_suspension_id=last_time_suspension_id,
#                 # last_time_suspension=last_time_suspension,
#                 # measures=implementing_measures,
#                 # users_ids=users_ids,
#                 # suspensions_list=suspensions_list,
#                 # response=response.json(),
#             )
#     users_ids_after_remove = await remove_all(async_db, User)  # delete all to clean the database and isolate tests
#     assert users_ids_after_remove == [], f"Users haven't been deleted: {users_ids_after_remove}"
#     suspensions_ids_after_remove = await remove_all(async_db, Suspension)  # delete all to clean the database
#     assert suspensions_ids_after_remove == [], f"Suspensions haven't been deleted: {suspensions_ids_after_remove}"
#     await log.ainfo("test_suspension_analytics", users_ids_after_remove=users_ids_after_remove,
#                     suspensions_ids_after_remove=suspensions_ids_after_remove)