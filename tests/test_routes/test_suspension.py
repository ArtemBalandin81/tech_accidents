"""
Асинхронные тесты работы эндпоинтов простоев: tests/test_routes/test_suspension.py
pytest -s -W ignore::DeprecationWarning
pytest -k test_unauthorized_get_urls -vs
pytest -k test_suspension.py -vs  # тесты только из этого файла
pytest -vs  # все тесты
https://anyio.readthedocs.io/en/stable/testing.html

pytest -k test_unauthorized_tries_suspension_urls -vs
pytest -k test_user_get_suspension_analytics_url -vs  TODO failed
pytest -k test_user_post_suspension_form_url -vs
pytest -k test_user_post_suspension_with_files_form_url -vs
pytest -k test_user_patch_suspension_url -vs
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
            assert response.status_code == status, (
                f"test_url: {api_url} with params: {params} is not {status}. Response: {response}"
            )
            await log.ainfo(
                "{}".format(api_url), response=response.json(), status=response.status_code, request=response._request
            )
        for api_url, data, status in patch_data_urls:
            response = await ac.patch(api_url, data=data)
            assert response.status_code == status, (
                f"test_url: {api_url} with data: {data} is not {status}. Response: {response}"
            )
            await log.ainfo(
                "{}".format(api_url), data=data, response=response.json(), status=response.status_code,
                request=response._request,
            )
        for api_url, data, status in post_data_urls:
            response = await ac.post(api_url, data=data)
            assert response.status_code == status, (
                f"test_url: {api_url} with data: {data} is not {status}. Response: {response}"
            )
            await log.ainfo(
                "{}".format(api_url), data=data, response=response.json(), status=response.status_code,
                request=response._request,
            )
            # print(f'response: {dir(response)}')

async def test_user_get_suspension_analytics_url(  # TODO - in this test an error!!!
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
        (user_orm_login, {ANALYTICS_START: now, ANALYTICS_FINISH: error_in_time}, 422, None, None, [], []),  # 12 regex
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
            assert response.status_code == status, f"User: {login} couldn't get {test_url}. Details: {response.json()}"
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
                f"****************  SCENARIO: ___ {scenario_number} ___  *******************************",
                login_data=login,
                params=search_params,
                status=response.status_code,
                suspensions_in_mins_total=total_minutes,
                suspensions_total=response.json().get(SUSPENSION_TOTAl),
                last_time_suspension_id=last_time_suspension_id,
                last_time_suspension=last_time_suspension,
                measures=implementing_measures,
                users_ids=users_ids,
                suspensions_list=suspensions_list,
                wings_of_end=f"_______________________________________________ END of SCENARIO: ___ {scenario_number}"
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
            ANALYTICS_START: now,
            ANALYTICS_FINISH: error_in_date,
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
            assert response.status_code == status, f"User: {login} couldn't get {test_url}. Response: {response}"
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
            await log.ainfo(
                f"****************  SCENARIO: ___ {scenario_number} ___  *******************************",
                login_data=login,
                params=create_params,
                files_in_db=files_in_db,
                files_attached=files_attached,
                files_in_response=files_in_response,
                files_dir=FILES_DIR,
                suspension_files_data=suspension_files_data,
                response=response.json(),
                wings_of_end=f"_______________________________________________ END of SCENARIO: ___ {scenario_number}"
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
    await log.ainfo("post_suspension_form_url", users_ids_after_remove=users_ids_after_remove,
                    suspensions_ids_after_remove=suspensions_ids_after_remove,
                    files_ids_after_remove=files_ids_after_remove)


async def test_user_post_suspension_with_files_form_url(  # todo  Несоответствие в таблицах SuspensionFiles и Files: [1, 2][]
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
            ANALYTICS_START: now,
            ANALYTICS_FINISH: error_in_date,
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
            assert response.status_code == status, f"User: {login} couldn't get {test_url}. Response: {response}"
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

            await log.ainfo(
                f"****************  SCENARIO: ___ {scenario_number} ___  *******************************",
                login_data=login,
                params=create_params,
                files_in_db=files_in_db,
                files_attached=files_attached,
                files_in_response=files_in_response,
                files_dir=FILES_DIR,
                suspension_files_data=suspension_files_data,
                response=response.json(),
                wings_of_end=f"_______________________________________________ END of SCENARIO: ___ {scenario_number}"
            )
            await delete_files_in_folder(file_paths)  # delete test files in folder
            suspensions_ids_after_remove = await remove_all(async_db, Suspension)  # delete all to clean the database
            assert suspensions_ids_after_remove == [], f"Suspensions are still in db: {suspensions_ids_after_remove}"
            suspension_files_data_after_remove = await remove_all(async_db, SuspensionsFiles)  # to clean the database
            assert suspension_files_data_after_remove == [], (
                f"SuspensionsFiles are still in db: {suspension_files_data_after_remove}"
            )

    users_ids_after_remove = await remove_all(async_db, User)  # delete all to clean the database and isolate tests
    assert users_ids_after_remove == [], f"Users haven't been deleted: {users_ids_after_remove}"
    suspensions_ids_after_remove = await remove_all(async_db, Suspension)  # delete all to clean the database
    assert suspensions_ids_after_remove == [], f"Suspensions haven't been deleted: {suspensions_ids_after_remove}"
    files_ids_after_remove = await remove_all(async_db, FileAttached)  # delete files to clean the database
    assert files_ids_after_remove == [], f"Files attached haven't been deleted: {files_ids_after_remove}"
    await log.ainfo("post_suspension_with_files_form_url", users_ids_after_remove=users_ids_after_remove,
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

    before_patched - параметры простоя при его создании: тождественны "scenarios" из suspensions_orm в confest.py

    create_scenarios - тестовые сценарии редактирования простоев.
    Параметры простоев не сбрасываются на базовые ("scenarios" из suspensions_orm в confest.py) в цикле сценариев,
    поэтому используем разные сценарии при тестировании редактирования параметров простая.

    expected - словарь ожидаемых значений параметров простоя:
    если в эндпоинте параметр меняется, то изменяется значение и в словаре, либо берется из БД (при создании простоя).

    match_values - кортеж параметров, используемых в assert (ожидание - реальность).

    """
    test_url = SUSPENSIONS_PATH+"/"  # /api/suspensions/{suspension_id}
    user_orm_email = "user_fixture@f.com"
    user_orm_login = {"username": user_orm_email, "password": "testings"}
    user_from_db = await async_db.scalar(select(User).where(User.email == user_orm_email))
    now = datetime.now(TZINFO).strftime(DATE_TIME_FORMAT)
    day_ago = (datetime.now(TZINFO) - timedelta(days=1)).strftime(DATE_TIME_FORMAT)
    error_in_date = "11-07-20244: 18:45"
    error_in_time = "11-07-2024: 45:18"
    test_files = ["testfile.txt", "testfile2.txt", "testfile3.txt"]
    for file_name in test_files:
        if not os.path.exists(TEST_ROUTES_DIR.joinpath(file_name)):
            with open(TEST_ROUTES_DIR.joinpath(file_name), "w") as file:
                file.write(f"{file_name} has been created: {now}")
    risk_accident_before_patched = next(iter(json.loads(settings.RISK_SOURCE).values()))  # 1st in dictionary
    tech_process_before_patched = next(iter(json.loads(settings.TECH_PROCESS).values()))  # 1st in dictionary :int = 25
    before_patched = (
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
    scenario_number = 0
    # параметры простоев не сбрасываются на базовые ("scenarios" из suspensions_orm в confest.py) в цикле сценариев,
    # поэтому используем разные сценарии при тестировании редактирования простоев todo
    create_scenarios = (
        # login, params, status, uploaded_file, suspension_id
        (user_orm_login, {
            ANALYTICS_START: error_in_time,
            ANALYTICS_FINISH: day_ago,
            SUSPENSION_DESCRIPTION: "test_description",
            IMPLEMENTING_MEASURES: "test_measures",
            TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
            RISK_ACCIDENT_SOURCE: json.loads(settings.RISK_SOURCE)["ANOTHER"]
        }, 422, None, 1),  # 1 error_in_time
        (user_orm_login, {
            ANALYTICS_START: error_in_date,
            ANALYTICS_FINISH: day_ago,
            SUSPENSION_DESCRIPTION: "test_description",
            IMPLEMENTING_MEASURES: "test_measures",
            TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
            RISK_ACCIDENT_SOURCE: json.loads(settings.RISK_SOURCE)["ANOTHER"]
        }, 422, None, 1),  # 2 error_in_date
        (user_orm_login, {
            ANALYTICS_START: now,
            ANALYTICS_FINISH: day_ago,
            SUSPENSION_DESCRIPTION: "test_description",
            IMPLEMENTING_MEASURES: "test_measures",
            TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
            RISK_ACCIDENT_SOURCE: json.loads(settings.RISK_SOURCE)["ANOTHER"]
        }, 422, None, 1),  # 3 L > R
        (user_orm_login, {
            IMPLEMENTING_MEASURES: "Just a single parameter has changed",
            FILES_UNLINK: False
        }, 200, None, 1),  # 4 Just a single parameter has changed
        (user_orm_login, {
            IMPLEMENTING_MEASURES: "Cause the measures have been changed in scenario 4 need to edit again",
            FILES_UNLINK: True
        }, 200, [], 1),  # 5 FILES_UNLINK TRUE when there is no files
        (user_orm_login, {}, 200, None, 2),  # 6 empty params / suspension_id = 2
        (user_orm_login, {
            ANALYTICS_START: day_ago,
            ANALYTICS_FINISH: now,
            SUSPENSION_DESCRIPTION: "test_description_patched",
            IMPLEMENTING_MEASURES: "test_measures",
            TECH_PROCESS: json.loads(settings.TECH_PROCESS)["SPEC_DEP_26"],
            RISK_ACCIDENT_SOURCE: json.loads(settings.RISK_SOURCE)["ANOTHER"],
            FILES_UNLINK: False
        }, 200, None, 1),  # 7 with params / suspension_id = 1
        # empty params with 1 file, suspension_id = 2
        (user_orm_login, {}, 200, {"file_to_upload": open(TEST_ROUTES_DIR.joinpath(test_files[0]), "rb")}, 2),  # 8
        # add 1 more file (total 2 files), suspension_id = 2
        (user_orm_login, {}, 200, {"file_to_upload": open(TEST_ROUTES_DIR.joinpath(test_files[1]), "rb")}, 2),  # 9
        # add 1 more file (total 3 files), suspension_id = 2
        (user_orm_login, {}, 200, {"file_to_upload": open(TEST_ROUTES_DIR.joinpath(test_files[2]), "rb")}, 2),  # 10
        (
            user_orm_login,
            {FILES_UNLINK: True}, 406, {"file_to_upload": open(TEST_ROUTES_DIR.joinpath(test_files[2]), "rb")}, 2
        ),  # 11 unlink files simultaneously with upload
        (user_orm_login, {FILES_UNLINK: True}, 200, None, 2),  # 12 and now unlink all the files
    )
    async with async_client as ac:
        for login, create_params, status, uploaded_file, suspension_id in create_scenarios:
            scenario_number += 1
            await log.ainfo(f"*************  SCENARIO: ___ {scenario_number} ___  *******************************")
            # gather info of objects in db before testing:
            objects_before = await async_db.scalars(select(Suspension))  # сколько объектов до сценария
            objects_in_db_before = objects_before.all()  # сколько объектов до сценария
            suspension_files_object_before = await async_db.scalars(select(SuspensionsFiles))
            suspension_files_in_db_before = suspension_files_object_before.all()
            attached_files_objects_before = await async_db.scalars(  # какие файлы были привязаны к простою
                select(FileAttached)
                .join(Suspension.files)
                .where(Suspension.id == suspension_id)
            )
            attached_files_in_db_before = attached_files_objects_before.all()
            attached_files_paths_before = [
                FILES_DIR.joinpath(file.name) for file in attached_files_in_db_before
                if attached_files_in_db_before is not None
            ]

            if suspension_files_in_db_before:
                suspension_files_records_before = [
                    (record.suspension_id, record.file_id) for record in suspension_files_in_db_before
                ]
            else:
                suspension_files_records_before = []

            response_login_user = await ac.post(LOGIN, data=login)
            response = await ac.patch(
                test_url + f"{suspension_id}",
                params=create_params,
                headers={"Authorization": f"Bearer {response_login_user.json()['access_token']}"},
                files=uploaded_file
            )
            assert response.status_code == status, f"User: {login} couldn't get {test_url}. Response: {response}"
            # print(f'Response: {response}')
            if response.status_code != 200:
                await log.ainfo(
                    f"SCENARIO: _{scenario_number}_ info: ",
                    login_data=login,
                    orm_before_patched={
                        "orm_description": before_patched[suspension_id - 1][0],
                        "orm_start": before_patched[suspension_id - 1][1].strftime(DATE_TIME_FORMAT),
                        "orm_finish": before_patched[suspension_id - 1][2].strftime(DATE_TIME_FORMAT),
                        "duration": before_patched[suspension_id - 1][2] - before_patched[suspension_id - 1][1],
                    },
                    params=create_params,
                    response=response.json(),
                    wings_of_end=f"_______________________________________ END of SCENARIO: ___ {scenario_number}"
                )
                continue
            # patched suspensions:
            objects = await async_db.scalars(select(Suspension))
            objects_in_db = objects.all()
            patched = objects_in_db[suspension_id-1] if objects_in_db is not None else None

            # patched files:
            files_in_response = response.json().get(FILES_SET_TO)
            file_objects = await async_db.scalars(select(FileAttached))  # == [] when no files attached
            files_in_db = file_objects.all() if file_objects is not None else []
            file_paths = [
                FILES_DIR.joinpath(file_name) for file_name in files_in_response if files_in_response is not None
            ]
            all_files_in_folder = [file.name for file in FILES_DIR.glob('*')]

            # patched files relations:
            suspension_files_object = await async_db.scalars(select(SuspensionsFiles))
            suspension_files_in_db = suspension_files_object.all()
            suspension_files_records = set(
                ((record.suspension_id, record.file_id) for record in suspension_files_in_db)
            )
            if uploaded_file and (create_params.get(FILES_UNLINK) is not True):
                suspension_files_in_scenario = (
                        tuple(suspension_files_records_before)
                        + ((suspension_id, len(suspension_files_records_before) + 1),)
                )
            elif create_params.get(FILES_UNLINK):
                suspension_files_in_scenario = ()
            else:
                suspension_files_in_scenario = tuple(suspension_files_records_before)

            # expected values in scenario
            expected = {
                "total_suspensions_expected": len(objects_in_db_before),
                "files_attached": await get_file_names_for_model_db(async_db, Suspension, patched.id),
                "suspension_files": suspension_files_in_scenario,
                "start": (
                    create_params.get(ANALYTICS_START) if create_params.get(ANALYTICS_START) is not None
                    else before_patched[suspension_id-1][1].strftime(DATE_TIME_FORMAT)
                ),
                "finish": (
                    create_params.get(ANALYTICS_FINISH) if create_params.get(ANALYTICS_FINISH) is not None
                    else before_patched[suspension_id-1][2].strftime(DATE_TIME_FORMAT)
                ),
                "description": (
                    create_params.get(SUSPENSION_DESCRIPTION) if create_params.get(SUSPENSION_DESCRIPTION) is not None
                    else before_patched[suspension_id-1][0]
                ),
                "measures": (
                    create_params.get(IMPLEMENTING_MEASURES) if create_params.get(IMPLEMENTING_MEASURES) is not None
                    else before_patched[suspension_id - 1][3]
                ),
                "risk_accident": (
                    create_params.get(RISK_ACCIDENT_SOURCE) if create_params.get(RISK_ACCIDENT_SOURCE) is not None
                    else risk_accident_before_patched
                ),
                "tech_process": (
                    create_params.get(TECH_PROCESS) if create_params.get(TECH_PROCESS) is not None
                    else tech_process_before_patched
                ),
            }

            # run asserts in a scenario:
            match_values = (
                # name value, expected_value, exist_value
                ("Suspension id: ", suspension_id, patched.id),
                ("Suspension user_id: ", user_from_db.id, patched.user_id),
                ("Total suspensions: ", expected.get("total_suspensions_expected"), len(objects_in_db)),
                ("Attached files: ", set(expected.get("files_attached")), set(files_in_response)),
                ("Suspension files: ", set(expected.get("suspension_files")), suspension_files_records),  # TODO
                ("Suspension start: ", expected.get("start"), patched.suspension_start.strftime(DATE_TIME_FORMAT)),
                ("Suspension finish: ", expected.get("finish"), patched.suspension_finish.strftime(DATE_TIME_FORMAT)),
                ("Description: ", expected.get("description"), patched.description),
                ("Implementing measures: ", expected.get("measures"), patched.implementing_measures),
                ("Risk accident: ", expected.get("risk_accident"), patched.risk_accident),
                ("Tech_process: ", int(expected.get("tech_process")), patched.tech_process),
                (
                    "Duration: ",
                    (
                            datetime.strptime(expected["finish"], DATE_TIME_FORMAT)
                            - datetime.strptime(expected["start"], DATE_TIME_FORMAT)
                    ),
                    patched.suspension_finish - patched.suspension_start
                ),
                # (": ",),
            )
            for name, expected_value, exist_value in match_values:
                assert expected_value == exist_value, f"{name} {exist_value} not as expected: {expected_value}"
            if files_in_response is not None:
                for file in files_in_response:
                    assert file in all_files_in_folder, f"Can't find: {file} in files folder: {FILES_DIR}"
            if create_params.get(FILES_UNLINK) is True and attached_files_paths_before:
                for file in attached_files_paths_before:
                    assert file.name not in all_files_in_folder, f"File: {file} is not deleted in folder: {FILES_DIR}"

            await log.ainfo(
                f"SCENARIO: _{scenario_number}_ info: ",
                files_attached_before=attached_files_paths_before,
                files_attached_expected=expected.get("files_attached"),
                files_in_db=files_in_db,
                files_in_response=files_in_response,
                file_paths=file_paths,
                login_data=login,
                orm_before_patched={
                    "orm_description": before_patched[suspension_id - 1][0],
                    "orm_start": before_patched[suspension_id - 1][1].strftime(DATE_TIME_FORMAT),
                    "orm_finish": before_patched[suspension_id - 1][2].strftime(DATE_TIME_FORMAT),
                    "duration": before_patched[suspension_id - 1][2] - before_patched[suspension_id - 1][1],
                },
                params=create_params,
                response=response.json(),
                suspension_files_expected=set(expected.get("suspension_files")),
                wings_of_end=f"_______________________________________________ END of SCENARIO: ___ {scenario_number}"
            )

    # cleaning the db and folders after test:
    users_ids_after_remove = await remove_all(async_db, User)  # delete all to clean the database and isolate tests
    assert users_ids_after_remove == [], f"Users haven't been deleted: {users_ids_after_remove}"
    suspensions_ids_after_remove = await remove_all(async_db, Suspension)  # delete all to clean the database
    assert suspensions_ids_after_remove == [], f"Suspensions haven't been deleted: {suspensions_ids_after_remove}"
    files_ids_after_remove = await remove_all(async_db, FileAttached)  # delete files to clean the database
    assert files_ids_after_remove == [], f"Files attached haven't been deleted: {files_ids_after_remove}"
    suspension_files_data_after_remove = await remove_all(async_db, SuspensionsFiles)  # clean the database
    assert suspension_files_data_after_remove == [], (
        f"SuspensionsFiles are still in db: {suspension_files_data_after_remove}"
    )
    await log.ainfo(
        "patch_suspension_form_url",
        users_ids_after_remove=users_ids_after_remove,
        suspensions_ids_after_remove=suspensions_ids_after_remove,
        files_ids_after_remove=files_ids_after_remove,
        suspension_files_after_remove=suspension_files_data_after_remove
    )

# TODO вместо regex использовать валидатор преобразования введенной даты тхт в дату: если не может - бросать ислючение


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