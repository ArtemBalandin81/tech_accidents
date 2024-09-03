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
from src.core.db.models import FileAttached, User, Suspension, SuspensionsFiles
from src.core.enums import TechProcess
from src.settings import settings

from tests.conftest import delete_files_in_folder, get_file_names_for_model_db, remove_all


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
         3, 2936, ["1", "2", "4"], [1, 2]),  # 6  "now" time difference in seconds: don't include last_time_suspension
        (user_orm_login, {ANALYTICS_START: two_days_ago, ANALYTICS_FINISH: last_time_suspension_exp_corrections}, 200,
         4, 2946, ["1", "2", "3", "4"], [1, 2]),  # 7  corrects the 6th scenario for time needed for tests running
        (user_orm_login, {ANALYTICS_START: now, ANALYTICS_FINISH: now}, 200, 0, 0, [], []),  # 8
        (user_orm_login, {ANALYTICS_START: now, ANALYTICS_FINISH: day_ago}, 422, None, None, [], []),  # 9 L > R
        (user_orm_login, {ANALYTICS_START: day_ago, ANALYTICS_FINISH: now, USER_MAIL: "unknown_user@f.com"}, 422,
         None, None, [], []),  # 10 filter by unknown_user
        (user_orm_login, {ANALYTICS_START: error_in_date, ANALYTICS_FINISH: now}, 422, None, None, [], []),  # 11 regex
        (user_orm_login, {ANALYTICS_START: error_in_time, ANALYTICS_FINISH: now}, 422, None, None, [], []),  # 12 regex
    )
    async with async_client as ac:
        for login, search_params, status, count, minutes, measures, ids_users in search_scenarios:
            response_login_user = await ac.post(LOGIN, data=login)
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
            await log.awarning(
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
) -> None:
    """
    Тестирует фиксацию случая простоя из формы с возможностью загрузки 1 файла:
    pytest -k test_user_post_suspension_form_url -vs
    """
    test_url = SUSPENSIONS_PATH+POST_SUSPENSION_FORM  # /api/suspensions/post_suspension_form
    user_orm_email = "user_fixture@f.com"
    user_orm_login = {"username": user_orm_email, "password": "testings"}
    now = datetime.now(TZINFO).strftime(DATE_TIME_FORMAT)
    day_ago = (datetime.now(TZINFO) - timedelta(days=1)).strftime(DATE_TIME_FORMAT)
    error_in_date = "11-07-20244: 18:45"
    error_in_time = "11-07-2024: 45:18"
    file_uploaded_name = "testfile.txt"
    if not os.path.exists(TEST_ROUTES_DIR.joinpath(file_uploaded_name)):
        with open(TEST_ROUTES_DIR.joinpath(file_uploaded_name), "w") as file:
            file.write(f"{file_uploaded_name} has been created: {now}")
    file_to_upload = {"file_to_upload": open(TEST_ROUTES_DIR.joinpath(file_uploaded_name), "rb")}
    total_suspensions_expected = 1
    suspensions_expected_id = 1
    scenario_number = 0
    create_scenarios = (
        # login, params, status, file_to_upload
        (user_orm_login, {
            ANALYTICS_START: error_in_time,
            ANALYTICS_FINISH: day_ago,
            SUSPENSION_DESCRIPTION: "test_description",
            IMPLEMENTING_MEASURES: "test_measures",
            TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
            RISK_ACCIDENT_SOURCE: json.loads(settings.RISK_SOURCE)["ANOTHER"]
        }, 422, None),  # 1 error_in_time
        (user_orm_login, {
            ANALYTICS_START: error_in_date,
            ANALYTICS_FINISH: day_ago,
            SUSPENSION_DESCRIPTION: "test_description",
            IMPLEMENTING_MEASURES: "test_measures",
            TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
            RISK_ACCIDENT_SOURCE: json.loads(settings.RISK_SOURCE)["ANOTHER"]
        }, 422, None),  # 2 error_in_date
        (user_orm_login, {
            ANALYTICS_START: now,
            ANALYTICS_FINISH: day_ago,
            SUSPENSION_DESCRIPTION: "test_description",
            IMPLEMENTING_MEASURES: "test_measures",
            TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
            RISK_ACCIDENT_SOURCE: json.loads(settings.RISK_SOURCE)["ANOTHER"]
        }, 422, None),  # 3 L > R
        (user_orm_login, {
            ANALYTICS_START: day_ago,
            ANALYTICS_FINISH: now,
            SUSPENSION_DESCRIPTION: "test_description",
            IMPLEMENTING_MEASURES: "test_measures",
            TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
            RISK_ACCIDENT_SOURCE: json.loads(settings.RISK_SOURCE)["ANOTHER"]
        }, 200, None),  # 4 - no file to upload
        (user_orm_login, {
            ANALYTICS_START: day_ago,
            ANALYTICS_FINISH: now,
            SUSPENSION_DESCRIPTION: "test_description",
            IMPLEMENTING_MEASURES: "test_measures",
            TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
            RISK_ACCIDENT_SOURCE: json.loads(settings.RISK_SOURCE)["ANOTHER"]
        }, 200, file_to_upload),  # 5 with file
    )
    async with async_client as ac:
        for login, create_params, status, files in create_scenarios:
            scenario_number += 1
            response_login_user = await ac.post(LOGIN, data=login)
            response = await ac.post(
                test_url,
                params=create_params,
                headers={"Authorization": f"Bearer {response_login_user.json()['access_token']}"},
                files=files,  # "=None" is possible
            )
            assert response.status_code == status, f"User: {login} couldn't get {test_url}"
            suspensions = await async_db.scalars(select(Suspension))
            suspensions_list = suspensions.all()
            suspension_files_object = await async_db.scalars(select(SuspensionsFiles))
            suspension_files_all = suspension_files_object.all()
            suspension_files_data = [record for record in suspension_files_all]
            file_objects = await async_db.scalars(select(FileAttached))
            files_in_db = file_objects.all()
            if len(suspensions_list) == 0:
                continue
            new_object = suspensions_list[0] if suspensions_list is not None else None
            total_suspensions = len(suspensions_list) if suspensions_list is not None else None
            files_attached = await get_file_names_for_model_db(async_db, Suspension, new_object.id)
            files_in_response = response.json().get(FILES_SET_TO)
            all_files_in_folder = [file.name for file in FILES_DIR.glob('*')]
            file_paths = [FILES_DIR.joinpath(file_name) for file_name in files_in_response]
            duration_db = new_object.suspension_finish - new_object.suspension_start
            duration_params = (
                    datetime.strptime(create_params[ANALYTICS_FINISH], DATE_TIME_FORMAT)
                    - datetime.strptime(create_params[ANALYTICS_START], DATE_TIME_FORMAT)
            )
            user_from_db = await async_db.scalar(select(User).where(User.email == user_orm_email))
            assert total_suspensions == total_suspensions_expected, (
                f"Total suspensions: {total_suspensions} are not as expected: {total_suspensions_expected}"
            )
            assert new_object.id == suspensions_expected_id, (
                f"Suspension id: {new_object.id} is not as expected: {suspensions_expected_id}"
            )
            assert new_object.user_id == user_from_db.id, (
                f"Suspension user_id: {new_object.user_id} is not as expected: {user_from_db.id}"
            )
            assert new_object.suspension_start.strftime(DATE_TIME_FORMAT) == create_params.get(ANALYTICS_START), (
                f"Suspension start: {new_object.suspension_start.strftime(DATE_TIME_FORMAT)}"
                f" is not: {create_params.get(ANALYTICS_START)}"
            )
            assert new_object.suspension_finish.strftime(DATE_TIME_FORMAT) == create_params.get(ANALYTICS_FINISH), (
                f"Suspension finish: {new_object.suspension_finish.strftime(DATE_TIME_FORMAT)}"
                f" is not: {create_params.get(ANALYTICS_FINISH)}"
            )
            assert new_object.implementing_measures == create_params.get(IMPLEMENTING_MEASURES), (
                f"Measures: {new_object.implementing_measures} are not: {create_params.get(IMPLEMENTING_MEASURES)}"
            )
            assert files_attached == files_in_response, (
                f"Attached files: {files_attached} are not as expected: {files_in_response}"
            )
            assert new_object.risk_accident == create_params.get(RISK_ACCIDENT_SOURCE), (
                f"Risk_accident: {new_object.risk_accident} "
                f"is not as expected: {create_params.get(RISK_ACCIDENT_SOURCE)}"
            )
            assert new_object.tech_process == int(create_params.get(TECH_PROCESS)), (
                f"Tech_process: {new_object.tech_process}"  # TechProcess(str(new_object.tech_process)).name = DU_25
                f" is not: {int(create_params.get(TECH_PROCESS))}"
            )
            assert duration_db == duration_params, f"Duration db: {duration_db} is not as expected: {duration_params}"

            if files is not None:
                file_db_name = [file.name for file in files_in_db][0].split("_")[2]
                assert files_in_response[0].split("_")[2] == file_uploaded_name, (
                    f"Files in response: {files_in_response} is not as expected: {file_uploaded_name}"
                )
                assert file_db_name == file_uploaded_name, (
                    f"File in database: {file_db_name} is not as expected: {file_uploaded_name}"
                )
                assert files_in_response[0] in all_files_in_folder, (
                    f"Can't find: {files_in_response[0]} in files folder: {FILES_DIR}"
                )
                assert suspension_files_data[0].suspension_id == suspension_files_data[0].file_id, (
                    f"Can't find record: {suspension_files_data[0]} in SuspensionsFiles: {suspension_files_data}"
                )  # record in SuspensionsFiles has been written
            await log.awarning(
                f"scenario_number: {scenario_number} ",
                login_data=login,
                params=create_params,
                files_in_db=files_in_db,
                files_attached=files_attached,
                files_in_response=files_in_response,
                files_dir=FILES_DIR,
                suspension_files_data=suspension_files_data,
                response=response.json()
            )
            await delete_files_in_folder(file_paths)  # delete test files in folder
            suspensions_ids_after_remove = await remove_all(async_db, Suspension)  # delete all to clean the database
            assert suspensions_ids_after_remove == [], f"Suspensions are still in db: {suspensions_ids_after_remove}"

    users_ids_after_remove = await remove_all(async_db, User)  # delete all to clean the database and isolate tests
    assert users_ids_after_remove == [], f"Users haven't been deleted: {users_ids_after_remove}"
    suspensions_ids_after_remove = await remove_all(async_db, Suspension)  # delete all to clean the database
    assert suspensions_ids_after_remove == [], f"Suspensions haven't been deleted: {suspensions_ids_after_remove}"
    files_ids_after_remove = await remove_all(async_db, FileAttached)  # delete files to clean the database
    assert files_ids_after_remove == [], f"Files attached haven't been deleted: {files_ids_after_remove}"
    await log.ainfo("test_user_post_suspension_form_url", users_ids_after_remove=users_ids_after_remove,
                    suspensions_ids_after_remove=suspensions_ids_after_remove,
                    files_ids_after_remove=files_ids_after_remove)


async def test_user_post_suspension_with_files_form_url(
        async_client: AsyncClient,
        async_db: AsyncSession,
        user_orm: User,
) -> None:
    """
    Тестирует фиксацию случая простоя из формы с обязательной загрузкой нескольких файлов:
    pytest -k test_user_post_suspension_with_files_form_url -vs
    """
    test_url = SUSPENSIONS_PATH+POST_SUSPENSION_FILES_FORM  # /api/suspensions/post_suspension_with_files_form
    user_orm_email = "user_fixture@f.com"
    user_orm_login = {"username": user_orm_email, "password": "testings"}
    now = datetime.now(TZINFO).strftime(DATE_TIME_FORMAT)
    day_ago = (datetime.now(TZINFO) - timedelta(days=1)).strftime(DATE_TIME_FORMAT)
    error_in_date = "11-07-20244: 18:45"
    error_in_time = "11-07-2024: 45:18"
    test_files = ["testfile.txt", "testfile2.txt"]
    for file_name in test_files:
        if not os.path.exists(TEST_ROUTES_DIR.joinpath(file_name)):
            with open(TEST_ROUTES_DIR.joinpath(file_name), "w") as file:
                file.write(f"{file_name} has been created: {now}")
    files = [
        ("files_to_upload", open(TEST_ROUTES_DIR.joinpath(test_files[0]), "rb")),
        ("files_to_upload", open(TEST_ROUTES_DIR.joinpath(test_files[1]), "rb"))
    ]
    total_suspensions_expected = 1
    suspensions_expected_id = 1
    scenario_number = 0
    create_scenarios = (
        # login, params, status, files
        (user_orm_login, {
            ANALYTICS_START: error_in_time,
            ANALYTICS_FINISH: day_ago,
            SUSPENSION_DESCRIPTION: "test_description",
            IMPLEMENTING_MEASURES: "test_measures",
            TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
            RISK_ACCIDENT_SOURCE: json.loads(settings.RISK_SOURCE)["ANOTHER"]
        }, 422, files),  # 1 error_in_time
        (user_orm_login, {
            ANALYTICS_START: error_in_date,
            ANALYTICS_FINISH: day_ago,
            SUSPENSION_DESCRIPTION: "test_description",
            IMPLEMENTING_MEASURES: "test_measures",
            TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
            RISK_ACCIDENT_SOURCE: json.loads(settings.RISK_SOURCE)["ANOTHER"]
        }, 422, files),  # 2 error_in_date
        (user_orm_login, {
            ANALYTICS_START: now,
            ANALYTICS_FINISH: day_ago,
            SUSPENSION_DESCRIPTION: "test_description",
            IMPLEMENTING_MEASURES: "test_measures",
            TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
            RISK_ACCIDENT_SOURCE: json.loads(settings.RISK_SOURCE)["ANOTHER"]
        }, 422, files),  # 3 L > R
        (user_orm_login, {
            ANALYTICS_START: day_ago,
            ANALYTICS_FINISH: now,
            SUSPENSION_DESCRIPTION: "test_description",
            IMPLEMENTING_MEASURES: "test_measures",
            TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
            RISK_ACCIDENT_SOURCE: json.loads(settings.RISK_SOURCE)["ANOTHER"]
        }, 422, None),  # 4 - no files to upload
        (user_orm_login, {
            ANALYTICS_START: day_ago,
            ANALYTICS_FINISH: now,
            SUSPENSION_DESCRIPTION: "test_description",
            IMPLEMENTING_MEASURES: "test_measures",
            TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
            RISK_ACCIDENT_SOURCE: json.loads(settings.RISK_SOURCE)["ANOTHER"]
        }, 422, []),  # 5 - no files to upload
        (user_orm_login, {
            ANALYTICS_START: day_ago,
            ANALYTICS_FINISH: now,
            SUSPENSION_DESCRIPTION: "test_description",
            IMPLEMENTING_MEASURES: "test_measures",
            TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
            RISK_ACCIDENT_SOURCE: json.loads(settings.RISK_SOURCE)["ANOTHER"]
        }, 200, files),  # 6 with files
    )
    async with async_client as ac:
        for login, create_params, status, files, in create_scenarios:
            scenario_number += 1
            response_login_user = await ac.post(LOGIN, data=login)
            response = await ac.post(
                test_url,
                params=create_params,
                headers={"Authorization": f"Bearer {response_login_user.json()['access_token']}"},
                files=files
            )
            assert response.status_code == status, f"User: {login} couldn't get {test_url}"
            suspensions_object = await async_db.scalars(select(Suspension))
            suspensions_list = suspensions_object.all()
            suspension_files_object = await async_db.scalars(select(SuspensionsFiles))
            suspension_files_all = suspension_files_object.all()
            suspension_files_data = [record for record in suspension_files_all]
            file_objects = await async_db.scalars(select(FileAttached))
            files_in_db = file_objects.all()
            if len(suspensions_list) == 0:
                continue
            new_object = suspensions_list[0] if suspensions_list is not None else None
            total_suspensions = len(suspensions_list) if suspensions_list is not None else None
            files_attached = await get_file_names_for_model_db(async_db, Suspension, new_object.id)
            files_in_response = response.json().get(FILES_SET_TO)
            all_files_in_folder = [file.name for file in FILES_DIR.glob('*')]
            file_paths = [FILES_DIR.joinpath(file_name) for file_name in files_in_response]
            duration_db = new_object.suspension_finish - new_object.suspension_start
            duration_params = (
                    datetime.strptime(create_params[ANALYTICS_FINISH], DATE_TIME_FORMAT)
                    - datetime.strptime(create_params[ANALYTICS_START], DATE_TIME_FORMAT)
            )
            user_from_db = await async_db.scalar(select(User).where(User.email == user_orm_email))
            assert total_suspensions == total_suspensions_expected, (
                f"Total suspensions: {total_suspensions} are not as expected: {total_suspensions_expected}"
            )
            assert new_object.id == suspensions_expected_id, (
                f"Suspension id: {new_object.id} is not as expected: {suspensions_expected_id}"
            )
            assert new_object.user_id == user_from_db.id, (
                f"Suspension user_id: {new_object.user_id} is not as expected: {user_from_db.id}"
            )
            assert new_object.suspension_start.strftime(DATE_TIME_FORMAT) == create_params.get(ANALYTICS_START), (
                f"Suspension start: {new_object.suspension_start.strftime(DATE_TIME_FORMAT)}"
                f" is not: {create_params.get(ANALYTICS_START)}"
            )
            assert new_object.suspension_finish.strftime(DATE_TIME_FORMAT) == create_params.get(ANALYTICS_FINISH), (
                f"Suspension finish: {new_object.suspension_finish.strftime(DATE_TIME_FORMAT)}"
                f" is not: {create_params.get(ANALYTICS_FINISH)}"
            )
            assert new_object.implementing_measures == create_params.get(IMPLEMENTING_MEASURES), (
                f"Measures: {new_object.implementing_measures} are not: {create_params.get(IMPLEMENTING_MEASURES)}"
            )
            assert files_attached == files_in_response, (
                f"Attached files: {files_attached} are not as expected: {files_in_response}"
            )
            assert new_object.risk_accident == create_params.get(RISK_ACCIDENT_SOURCE), (
                f"Risk_accident: {new_object.risk_accident} "
                f"is not as expected: {create_params.get(RISK_ACCIDENT_SOURCE)}"
            )
            assert new_object.tech_process == int(create_params.get(TECH_PROCESS)), (
                f"Tech_process: {new_object.tech_process}"  # TechProcess(str(new_object.tech_process)).name = DU_25
                f" is not: {int(create_params.get(TECH_PROCESS))}"
            )
            assert duration_db == duration_params, f"Duration db: {duration_db} is not as expected: {duration_params}"

            if files is not None:
                i = 0
                for file in files_in_response:
                    # print(f'File in response: {file.split("_")[2]} /// expected: {test_files[i]}')
                    assert file.split("_")[2] == test_files[i], (
                        f"File in response: {file} is not as expected: {test_files[i]}"
                    )
                    assert file in all_files_in_folder, f"Can't find: {file} in files folder: {FILES_DIR}"
                    assert [suspension_files_data[i].suspension_id, suspension_files_data[i].file_id] == [1, i+1], (
                        f"No record: {suspension_files_data[i]} in SuspensionsFiles: {suspension_files_data}"
                    )  # check record in SuspensionsFiles has been written
                    i += 1

            await log.awarning(
                f"scenario_number: {scenario_number} ",
                login_data=login,
                params=create_params,
                files_in_db=files_in_db,
                files_attached=files_attached,
                files_in_response=files_in_response,
                files_dir=FILES_DIR,
                suspension_files_data=suspension_files_data,
                response=response.json()
            )
            await delete_files_in_folder(file_paths)  # delete test files in folder
            suspensions_ids_after_remove = await remove_all(async_db, Suspension)  # delete all to clean the database
            assert suspensions_ids_after_remove == [], f"Suspensions are still in db: {suspensions_ids_after_remove}"

    users_ids_after_remove = await remove_all(async_db, User)  # delete all to clean the database and isolate tests
    assert users_ids_after_remove == [], f"Users haven't been deleted: {users_ids_after_remove}"
    suspensions_ids_after_remove = await remove_all(async_db, Suspension)  # delete all to clean the database
    assert suspensions_ids_after_remove == [], f"Suspensions haven't been deleted: {suspensions_ids_after_remove}"
    files_ids_after_remove = await remove_all(async_db, FileAttached)  # delete files to clean the database
    assert files_ids_after_remove == [], f"Files attached haven't been deleted: {files_ids_after_remove}"
    await log.ainfo("test_user_post_suspension_form_url", users_ids_after_remove=users_ids_after_remove,
                    suspensions_ids_after_remove=suspensions_ids_after_remove,
                    files_ids_after_remove=files_ids_after_remove)


async def test_user_patch_suspension_url(
        async_client: AsyncClient,
        async_db: AsyncSession,
        # user_orm: User,  # todo delete
        suspensions_orm: Suspension
) -> None:
    """
    Тестирует редактирование случая простоя из формы с возможностью дозагрузки файла:
    pytest -k test_user_patch_suspension_url -vs
    """
    test_url = SUSPENSIONS_PATH+"/"  # /api/suspensions/{suspension_id}
    user_orm_email = "user_fixture@f.com"
    user_orm_login = {"username": user_orm_email, "password": "testings"}
    now = datetime.now(TZINFO).strftime(DATE_TIME_FORMAT)
    day_ago = (datetime.now(TZINFO) - timedelta(days=1)).strftime(DATE_TIME_FORMAT)
    error_in_date = "11-07-20244: 18:45"
    error_in_time = "11-07-2024: 45:18"
    test_files = ["testfile.txt", "testfile2.txt"]
    for file_name in test_files:
        if not os.path.exists(TEST_ROUTES_DIR.joinpath(file_name)):
            with open(TEST_ROUTES_DIR.joinpath(file_name), "w") as file:
                file.write(f"{file_name} has been created: {now}")
    files = [
        ("files_to_upload", open(TEST_ROUTES_DIR.joinpath(test_files[0]), "rb")),
        ("files_to_upload", open(TEST_ROUTES_DIR.joinpath(test_files[1]), "rb"))
    ]
    file_to_upload = {"file_to_upload": open(TEST_ROUTES_DIR.joinpath(test_files[0]), "rb")}
    suspensions_before_patched = (
        (
            "_1_[]",  # description - [0],
            datetime.now() - timedelta(days=2),  # suspension_start - [1],
            datetime.now() - timedelta(days=1, hours=23, minutes=59),  # suspension_finish - [2],
            "1",  # measures - [3],
            1,  # user_id - [4],
        ),
        ("_[2875_]", datetime.now() - timedelta(days=2), datetime.now() - timedelta(minutes=5), "2", 2),
        ("[_10_]", datetime.now() - timedelta(minutes=15), datetime.now() - timedelta(minutes=5), "3", 1),
        ("[_60]_", datetime.now() - timedelta(minutes=30), datetime.now() + timedelta(minutes=30), "4", 2)
    )
    total_suspensions_expected = 4
    # suspensions_expected_id = 1
    scenario_number = 0
    create_scenarios = (
        # login, params, status, file_to_upload, suspension_id
        # (user_orm_login, {
        #     ANALYTICS_START: error_in_time,
        #     ANALYTICS_FINISH: day_ago,
        #     SUSPENSION_DESCRIPTION: "test_description",
        #     IMPLEMENTING_MEASURES: "test_measures",
        #     TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
        #     RISK_ACCIDENT_SOURCE: json.loads(settings.RISK_SOURCE)["ANOTHER"]
        # }, 422, file_to_upload, 1),  # 1 error_in_time
        # (user_orm_login, {
        #     ANALYTICS_START: error_in_date,
        #     ANALYTICS_FINISH: day_ago,
        #     SUSPENSION_DESCRIPTION: "test_description",
        #     IMPLEMENTING_MEASURES: "test_measures",
        #     TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
        #     RISK_ACCIDENT_SOURCE: json.loads(settings.RISK_SOURCE)["ANOTHER"]
        # }, 422, file_to_upload, 1),  # 2 error_in_date
        # (user_orm_login, {
        #     ANALYTICS_START: now,
        #     ANALYTICS_FINISH: day_ago,
        #     SUSPENSION_DESCRIPTION: "test_description",
        #     IMPLEMENTING_MEASURES: "test_measures",
        #     TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
        #     RISK_ACCIDENT_SOURCE: json.loads(settings.RISK_SOURCE)["ANOTHER"]
        # }, 422, file_to_upload, 1),  # 3 L > R
        # (user_orm_login, {
        #     ANALYTICS_START: day_ago,
        #     ANALYTICS_FINISH: now,
        #     SUSPENSION_DESCRIPTION: "test_description",
        #     IMPLEMENTING_MEASURES: "test_measures",
        #     TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
        #     RISK_ACCIDENT_SOURCE: json.loads(settings.RISK_SOURCE)["ANOTHER"]
        # }, 422, None, 1),  # 4
        # (user_orm_login, {
        #     ANALYTICS_START: day_ago,
        #     ANALYTICS_FINISH: now,
        #     SUSPENSION_DESCRIPTION: "test_description",
        #     IMPLEMENTING_MEASURES: "test_measures",
        #     TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
        #     RISK_ACCIDENT_SOURCE: json.loads(settings.RISK_SOURCE)["ANOTHER"]
        # }, 422, [], 1),  # 5
        (user_orm_login, {
            ANALYTICS_START: day_ago,
            ANALYTICS_FINISH: now,
            SUSPENSION_DESCRIPTION: "test_description_patched",
            # IMPLEMENTING_MEASURES: "test_measures",
            # TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
            # RISK_ACCIDENT_SOURCE: json.loads(settings.RISK_SOURCE)["ANOTHER"],
            FILES_UNLINK: False
        }, 200, None, 1),  # 6
    )
    async with async_client as ac:
        for login, create_params, status, file_to_upload, suspension_id in create_scenarios:
            scenario_number += 1
            response_login_user = await ac.post(LOGIN, data=login)
            response = await ac.patch(
                test_url + f"{suspension_id}",
                params=create_params,
                headers={"Authorization": f"Bearer {response_login_user.json()['access_token']}"},
                files=file_to_upload
            )
            # print(f'response: {response}')
            assert response.status_code == status, f"User: {login} couldn't get {test_url}"
            # suspensions:
            suspensions_object = await async_db.scalars(select(Suspension))
            suspensions_list = suspensions_object.all()
            total_suspensions = len(suspensions_list) if suspensions_list is not None else None
            patched_suspension = suspensions_list[suspension_id-1] if suspensions_list is not None else None
            start_expected = (
                create_params.get(ANALYTICS_START) if create_params.get(ANALYTICS_START) is not None
                else suspensions_before_patched[suspension_id-1][1].strftime(DATE_TIME_FORMAT)
            )
            finish_expected = (
                create_params.get(ANALYTICS_FINISH) if create_params.get(ANALYTICS_FINISH) is not None
                else suspensions_before_patched[suspension_id-1][2].strftime(DATE_TIME_FORMAT)
            )
            description_expected = (
                create_params.get(SUSPENSION_DESCRIPTION) if create_params.get(SUSPENSION_DESCRIPTION) is not None
                else suspensions_before_patched[suspension_id-1][0]
            )

            # files attached to suspensions:
            suspension_files_object = await async_db.scalars(select(SuspensionsFiles))
            suspension_files_all = suspension_files_object.all()
            suspension_files_data = [record for record in suspension_files_all]
            file_objects = await async_db.scalars(select(FileAttached))
            files_in_db = file_objects.all()
            files_attached = await get_file_names_for_model_db(async_db, Suspension, patched_suspension.id)
            all_files_in_folder = [file.name for file in FILES_DIR.glob('*')]
            files_in_response = response.json().get(FILES_SET_TO)
            if files_in_response is not None:
                file_paths = [FILES_DIR.joinpath(file_name) for file_name in files_in_response]

            duration_db = patched_suspension.suspension_finish - patched_suspension.suspension_start
            # duration_params = (
            #         datetime.strptime(create_params[ANALYTICS_FINISH], DATE_TIME_FORMAT)
            #         - datetime.strptime(create_params[ANALYTICS_START], DATE_TIME_FORMAT)
            # )
            user_from_db = await async_db.scalar(select(User).where(User.email == user_orm_email))
            assert total_suspensions == total_suspensions_expected, (
                f"Total suspensions: {total_suspensions} are not as expected: {total_suspensions_expected}"
            )
            assert patched_suspension.id == suspension_id, (
                f"Suspension id: {patched_suspension.id} is not as expected: {suspension_id}"
            )
            assert patched_suspension.user_id == user_from_db.id, (
                f"Suspension user_id: {patched_suspension.user_id} is not as expected: {user_from_db.id}"
            )
            # assert patched_suspension.suspension_start.strftime(DATE_TIME_FORMAT) == start_expected, (
            #     f"Suspension start: {patched_suspension.suspension_start.strftime(DATE_TIME_FORMAT)}"
            #     f" is not as expected: {start_expected}"
            # )
            # assert new_object.suspension_finish.strftime(DATE_TIME_FORMAT) == create_params.get(ANALYTICS_FINISH), (
            #     f"Suspension finish: {new_object.suspension_finish.strftime(DATE_TIME_FORMAT)}"
            #     f" is not: {create_params.get(ANALYTICS_FINISH)}"
            # )
            # assert new_object.implementing_measures == create_params.get(IMPLEMENTING_MEASURES), (
            #     f"Measures: {new_object.implementing_measures} are not: {create_params.get(IMPLEMENTING_MEASURES)}"
            # )
            # assert files_attached == files_in_response, (
            #     f"Attached files: {files_attached} are not as expected: {files_in_response}"
            # )
            # assert new_object.risk_accident == create_params.get(RISK_ACCIDENT_SOURCE), (
            #     f"Risk_accident: {new_object.risk_accident} "
            #     f"is not as expected: {create_params.get(RISK_ACCIDENT_SOURCE)}"
            # )
            # assert new_object.tech_process == int(create_params.get(TECH_PROCESS)), (
            #     f"Tech_process: {new_object.tech_process}"  # TechProcess(str(new_object.tech_process)).name = DU_25
            #     f" is not: {int(create_params.get(TECH_PROCESS))}"
            # )
            # assert duration_db == duration_params, f"Duration db: {duration_db} is not as expected: {duration_params}"
            #
            # if files is not None:
            #     i = 0
            #     for file in files_in_response:
            #         # print(f'File in response: {file.split("_")[2]} /// expected: {test_files[i]}')
            #         assert file.split("_")[2] == test_files[i], (
            #             f"File in response: {file} is not as expected: {test_files[i]}"
            #         )
            #         assert file in all_files_in_folder, f"Can't find: {file} in files folder: {FILES_DIR}"
            #         assert [suspension_files_data[i].suspension_id, suspension_files_data[i].file_id] == [1, i+1], (
            #             f"No record: {suspension_files_data[i]} in SuspensionsFiles: {suspension_files_data}"
            #         )  # check record in SuspensionsFiles has been written
            #         i += 1

            await log.awarning(
                f"scenario_number: {scenario_number} ",
                files_in_db=files_in_db,
                # files_attached=files_attached,
                # files_in_response=files_in_response,
                files_dir=FILES_DIR,
                login_data=login,
                orm_suspensions_before_patched={
                    "orm_description": suspensions_before_patched[suspension_id - 1][0],
                    "orm_start": suspensions_before_patched[suspension_id - 1][1].strftime(DATE_TIME_FORMAT),
                    "orm_finish": suspensions_before_patched[suspension_id - 1][2].strftime(DATE_TIME_FORMAT),
                },
                params=create_params,
                response=response.json(),
                suspension_files_data=suspension_files_data,
            )
            # await delete_files_in_folder(file_paths)  # delete test files in folder
            # suspensions_ids_after_remove = await remove_all(async_db, Suspension)  # delete all to clean the database
            # assert suspensions_ids_after_remove == [], f"Suspensions are still in db: {suspensions_ids_after_remove}"

    users_ids_after_remove = await remove_all(async_db, User)  # delete all to clean the database and isolate tests
    assert users_ids_after_remove == [], f"Users haven't been deleted: {users_ids_after_remove}"
    suspensions_ids_after_remove = await remove_all(async_db, Suspension)  # delete all to clean the database
    assert suspensions_ids_after_remove == [], f"Suspensions haven't been deleted: {suspensions_ids_after_remove}"
    files_ids_after_remove = await remove_all(async_db, FileAttached)  # delete files to clean the database
    assert files_ids_after_remove == [], f"Files attached haven't been deleted: {files_ids_after_remove}"
    await log.ainfo("test_user_post_suspension_form_url", users_ids_after_remove=users_ids_after_remove,
                    suspensions_ids_after_remove=suspensions_ids_after_remove,
                    files_ids_after_remove=files_ids_after_remove)

# TODO endpoints suspensions

# ANALYTICS = "/analytics"  # GET is done!
# POST_SUSPENSION_FORM = "/post_suspension_form"  # is done!
# POST_SUSPENSION_FILES_FORM = "/post_suspension_with_files_form"  # is done!

# SUSPENSION_ID = "/{suspension_id}"  # PATCH todo after /api/suspensions/{suspension_id}
# SUSPENSION_ID = "/{suspension_id}"  # DELETE todo /api/suspensions/{suspension_id}

# MY_SUSPENSIONS = "/my_suspensions"  # GET todo
# SUSPENSION_ID = "/{suspension_id}"  # GET todo
# MAIN_ROUTE = "/"   # GET all todo

# ADD_FILES_TO_SUSPENSION = "/add_files_to_suspension"  # POST todo