"""
Асинхронные тесты работы эндпоинтов простоев: tests/test_routes/test_suspension.py
pytest -s -W ignore::DeprecationWarning
pytest -k test_unauthorized_get_urls -vs
pytest -k test_suspension.py -vs  # тесты только из этого файла
pytest -vs  # все тесты
https://anyio.readthedocs.io/en/stable/testing.html

pytest -k test_unauthorized_tries_suspension_urls -vs
pytest -k test_user_get_suspension_analytics_url -vs
pytest -k test_user_get_suspension_url -vs
pytest -k test_user_get_all_suspension_url -vs
pytest -k test_user_get_my_suspension_url -vs
pytest -k test_user_post_suspension_form_url -vs
pytest -k test_user_post_suspension_with_files_form_url -vs
pytest -k test_user_patch_suspension_url -vs
pytest -k test_super_user_delete_suspension_url -vs

pytest -k test_super_user_add_files_to_suspension_url -vs

Для отладки рекомендуется использовать:
print(f'response_dir: {dir(response)}')
print(f'RESPONSE__dict__: {response.__dict__}')

"""
import json
import os
import sys
from pathlib import Path

import pytest
import structlog
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.api.constants import *
from src.core.db.models import FileAttached, Suspension, SuspensionsFiles, User
from src.settings import settings
from tests.conftest import (clean_test_database, create_test_files,
                            delete_files_in_folder,
                            get_file_names_for_model_db)

log = structlog.get_logger() if settings.FILE_NAME_IN_LOG is False else structlog.get_logger().bind(file_name=__file__)
pytestmark = pytest.mark.anyio  # make all test mark with `anyio` or use decorator: # @pytest.mark.anyio

SUSPENSIONS_PATH = settings.ROOT_PATH + "/suspensions"  # /api/suspensions/
FILES_PATH = settings.ROOT_PATH + "/files"  # /api/files/

SERVICES_DIR = Path(__file__).resolve().parent.parent.parent
FILES_DIR = SERVICES_DIR.joinpath(settings.FILES_DOWNLOAD_DIR)
TEST_ROUTES_DIR = Path(__file__).resolve().parent


async def test_unauthorized_tries_suspension_urls(async_client: AsyncClient) -> None:
    """
    Тестирует доступ к эндпоинтам простоев неавторизованным пользователем:
    pytest -k test_unauthorized_tries_suspension_urls -vs
    """
    get_params_urls = (
        (SUSPENSIONS_PATH + ANALYTICS, {}, 401),  # /api/suspensions/analytics
        (SUSPENSIONS_PATH + MAIN_ROUTE, {}, 401),  # /api/suspensions/
        (SUSPENSIONS_PATH + MY_SUSPENSIONS, {}, 401),  # /api/my_suspensions/
        (SUSPENSIONS_PATH + SUSPENSION_ID, {}, 401),  # /api/suspensions/{suspension_id}
    )
    delete_params_urls = (
        (SUSPENSIONS_PATH + SUSPENSION_ID, {}, 401),  # /api/suspensions/{suspension_id}
    )
    patch_data_urls = (
        (SUSPENSIONS_PATH + SUSPENSION_ID, {}, 401),  # /api/suspensions/{suspension_id}
    )
    post_data_urls = (
        (SUSPENSIONS_PATH + POST_SUSPENSION_FORM, {}, 401),  # /api/suspensions/post_suspension_form
        (SUSPENSIONS_PATH + POST_SUSPENSION_FILES_FORM, {}, 401),  # /api/suspensions/post_suspension_with_files_form
        (SUSPENSIONS_PATH + ADD_FILES_TO_SUSPENSION, {}, 401),  # /api/suspensions/add_files_to_suspension
    )
    async with async_client as ac:
        for api_url, params, status in get_params_urls:
            response = await ac.get(api_url, params=params)
            assert response.status_code == status, (
                f"test_url: {api_url} with params: {params} is not {status}. Response: {response.__dict__}"
            )
            await log.ainfo(
                "{}".format(api_url), response=response.json(), status=response.status_code, request=response._request
            )
        for api_url, params, status in delete_params_urls:
            response = await ac.delete(api_url, params=params)
            assert response.status_code == status, (
                f"test_url: {api_url} with params: {params} is not {status}. Response: {response.__dict__}"
            )
            await log.ainfo(
                "{}".format(api_url), response=response.json(), status=response.status_code, request=response._request
            )
        for api_url, data, status in patch_data_urls:
            response = await ac.patch(api_url, data=data)
            assert response.status_code == status, (
                f"test_url: {api_url} with data: {data} is not {status}. Response: {response.__dict__}"
            )
            await log.ainfo(
                "{}".format(api_url), data=data, response=response.json(), status=response.status_code,
                request=response._request,
            )
        for api_url, data, status in post_data_urls:
            response = await ac.post(api_url, data=data)
            assert response.status_code == status, (
                f"test_url: {api_url} with data: {data} is not {status}. Response: {response.__dict__}"
            )
            await log.ainfo(
                "{}".format(api_url), data=data, response=response.json(), status=response.status_code,
                request=response._request,
            )


async def test_user_get_suspension_analytics_url(
        async_client: AsyncClient,
        async_db: AsyncSession,
        suspensions_orm: Suspension
) -> None:
    """
    Тестирует доступ пользователя к эндпоинту аналитики:
    pytest -k test_user_get_suspension_analytics_url -vs
    """
    test_url = SUSPENSIONS_PATH + ANALYTICS  # /api/suspensions/analytics
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
        # login, params, status, count, minutes, measures, users_ids, name
        (
            user_settings_login, {ANALYTICS_START: day_ago, ANALYTICS_FINISH: now}, 200, 2, 70, ["3", "4"], [1, 2],
            "2 objects: [3, 4] with users_ids: [1, 2] 70 min total"
        ),  # 1
        (user_orm_login, {ANALYTICS_START: day_ago, ANALYTICS_FINISH: now, USER_MAIL: user_settings_email}, 200,
         1, 10, ["3"], [1], "filter by user_settings_email"),  # 2
        (user_orm_login, {ANALYTICS_START: now, ANALYTICS_FINISH: future_1_day}, 200, 0, 0, [], [], "None"),  # 3
        (user_orm_login, {ANALYTICS_START: last_time_suspension_expected, ANALYTICS_FINISH: future_1_day}, 200,
         1, 10, ["3"], [1], "last_time_suspension_expected"),  # 4
        (user_orm_login, {ANALYTICS_START: two_days_ago, ANALYTICS_FINISH: now}, 200,
         4, 2946, ["1", "2", "3", "4"], [1, 2], "test all suspensions: 2946 mins and 4 suspensions"),  # 5
        (user_orm_login, {ANALYTICS_START: two_days_ago, ANALYTICS_FINISH: last_time_suspension_expected}, 200,
         3, 2936, ["1", "2", "4"], [1, 2], "now time difference in seconds: don't include last_time_suspension"),  # 6
        (user_orm_login, {ANALYTICS_START: two_days_ago, ANALYTICS_FINISH: last_time_suspension_exp_corrections}, 200,
         4, 2946, ["1", "2", "3", "4"], [1, 2], "corrects the 6th scenario for time needed for tests running"),  # 7
        (user_orm_login, {ANALYTICS_START: now, ANALYTICS_FINISH: now}, 200, 0, 0, [], [], "now-now"),  # 8
        (user_orm_login, {ANALYTICS_START: now, ANALYTICS_FINISH: day_ago}, 422, None, None, [], [], "L > R"),  # 9
        (user_orm_login, {ANALYTICS_START: day_ago, ANALYTICS_FINISH: now, USER_MAIL: "unknown_user@f.com"}, 422,
         None, None, [], [], "filter by unknown_user"),  # 10
        (
            user_orm_login, {ANALYTICS_START: error_in_date, ANALYTICS_FINISH: now}, 422, None, None, [], [],
            "ANALYTICS_START: error_in_date"),  # 11
        (
            user_orm_login, {ANALYTICS_START: now, ANALYTICS_FINISH: error_in_time}, 422, None, None, [], [],
            "ANALYTICS_FINISH: error_in_time"),  # 12
    )
    async with async_client as ac:
        for login, search_params, status, count, minutes, measures, ids_users, name in search_scenarios:
            login_user_response = await ac.post(LOGIN, data=login)
            response = await ac.get(
                test_url,
                params=search_params,
                headers={"Authorization": f"Bearer {login_user_response.json()['access_token']}"},
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
            assert response.status_code == status, f"{login} couldn't get {test_url}. Details: {response.json()}"
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
                await log.ainfo(f"**************************************  SCENARIO: __ {scenario_number} __: {name}"),
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
                wings_of_end=f"______________________ END of SCENARIO: ___ {scenario_number} __ {name} __"
            )
    await clean_test_database(async_db, User, Suspension)


async def test_user_patch_suspension_url(
        async_client: AsyncClient,
        async_db: AsyncSession,
        suspensions_orm: Suspension,
        super_user_orm: User
) -> None:
    """
    Тестирует редактирование случая простоя из формы с возможностью дозагрузки файла:
    pytest -k test_user_patch_suspension_url -vs

    before_patched - параметры простоя при его создании: тождественны "scenarios" из suspensions_orm в confest.py

    scenarios - тестовые сценарии использования эндпоинта (сценарии не изолированы друг от друга).
    expected - словарь ожидаемых значений в сценарии.
    match_values - кортеж параметров, используемых в assert (ожидание - реальность).

    """
    test_url = SUSPENSIONS_PATH + "/"  # /api/suspensions/{suspension_id}
    user_orm_email = "user_fixture@f.com"
    user_orm_login = {"username": user_orm_email, "password": "testings"}
    user_settings_email = json.loads(settings.STAFF)["1"]
    user_settings_login = {"username": user_settings_email, "password": "testings"}
    super_user_login = {"username": super_user_orm.email, "password": "testings"}
    now = datetime.now(TZINFO).strftime(DATE_TIME_FORMAT)
    day_ago = (datetime.now(TZINFO) - timedelta(days=1)).strftime(DATE_TIME_FORMAT)
    error_in_date = "11-07-20244: 18:45"
    error_in_time = "11-07-2024: 45:18"
    test_files = ["testfile.txt", "testfile2.txt", "testfile3.txt"]
    await create_test_files(test_files)
    scenario_number = 0
    scenarios = (
        # login, params, status, uploaded_file, file_index, suspension_id, name - Dependant scenarios !!!
        (user_settings_login, {ANALYTICS_START: error_in_time}, 422, None, None, 1, "error_in_time"),  # 1
        (user_settings_login, {ANALYTICS_START: error_in_date}, 422, None, None, 1, "error_in_date"),  # 2
        (user_settings_login, {ANALYTICS_START: now, ANALYTICS_FINISH: day_ago}, 422, None, None, 1, "L > R"),  # 3
        (user_orm_login, {SUSPENSION_DESCRIPTION: "not author"}, 403, None, None, 1, "not author or admin"),  # 4
        (
            super_user_login,
            {SUSPENSION_DESCRIPTION: "admin", IMPLEMENTING_MEASURES: "admin"},
            200, None, None, 2, "admin changes description & measures Obj_id=1"
        ),  # 5
        (
            super_user_login,
            {SUSPENSION_DESCRIPTION: "admin changes description & upload file to Obj_id=3"},
            200, {"file_to_upload": open(TEST_ROUTES_DIR.joinpath(test_files[2]), "rb")}, 2, 3, "admin change & upload"
        ),  # 6 ['<Obj 3 - Files 1>']
        (
            user_orm_login,
            {
                ANALYTICS_START: day_ago,
                ANALYTICS_FINISH: now,
                SUSPENSION_DESCRIPTION: "user_orm changes all parameters & upload file to Obj_id=4",
                IMPLEMENTING_MEASURES: "test_measures",
                TECH_PROCESS: json.loads(settings.TECH_PROCESS)["SPEC_DEP_26"],
                RISK_ACCIDENT_SOURCE: json.loads(settings.RISK_SOURCE)["ANOTHER"],
                FILES_UNLINK: False
            },
            200, {"file_to_upload": open(TEST_ROUTES_DIR.joinpath(test_files[0]), "rb")}, 0, 4, "all parameters & file"
        ),  # 7 ['<Obj 3 - Files 1>', '<Obj 4 - Files 2>']
        (
            user_settings_login,
            {SUSPENSION_DESCRIPTION: "unlink if no files", FILES_UNLINK: True},
            200, None, None, 1, "unlink if no files in Obj_id = 1, but ['<Obj 3 - Files 1>', '<Obj 4 - Files 2>']"
        ),  # 8 ['<Obj 3 - Files 1>', '<Obj 4 - Files 2>']
        (user_settings_login, {}, 200, None, None, 1, "empty params in Obj_id = 1 edited"),  # 9
        (
            user_orm_login,
            {},
            200,
            {"file_to_upload": open(TEST_ROUTES_DIR.joinpath(test_files[1]), "rb")}, 1, 4, "file is added Obj 4 [_2]"
        ),  # 10 ['<Obj 3 - Files 1>', '<Obj 4 - Files 2>', '<Obj 4 - Files 3>']
        (
            user_orm_login,
            {},
            200,
            {"file_to_upload": open(TEST_ROUTES_DIR.joinpath(test_files[2]), "rb")}, 2, 4, "file is added Obj 4 [_3]"
        ),  # 11 ['<Obj 3 - Files 1>', '<Obj 4 - Files 2>', '<Obj 4 - Files 3>', '<Obj 4 - Files 4>']
        (
            user_orm_login,
            {FILES_UNLINK: True},
            406,
            {"file_to_upload": open(TEST_ROUTES_DIR.joinpath(test_files[0]), "rb")}, 0, 4, "unlink & upload at 1 time"
        ),  # 12
        (user_orm_login, {FILES_UNLINK: True}, 200, None, None, 4, "unlink files of Obj_id: 4"),  # 13 ['<T 3 - F 1>']
        (super_user_login, {FILES_UNLINK: True}, 200, None, None, 3, "unlink files of Obj_id: 3"),  # 14 []
    )
    async with async_client as ac:
        # !!!! starting testing scenarios:
        for login, create_params, status, uploaded_file, file_index, suspension_id, name in scenarios:
            scenario_number += 1
            await log.ainfo(f"**************************************  SCENARIO: __ {scenario_number} __: {name}")
            # grab info of objects in db before testing:
            objects_before = await async_db.scalars(select(Suspension))
            objects_in_db_before = objects_before.all()  # objects before scenarios have started
            object_before_to_patch = [_ for _ in objects_in_db_before if _.id == suspension_id][0]
            # file_names_attached_before:
            file_names_attached = await get_file_names_for_model_db(async_db, Suspension, suspension_id)
            file_names_attached_before = (
                [file.split("_")[-1] for file in file_names_attached if len(file_names_attached) > 0]
            )
            attached_files_paths_before = [
                FILES_DIR.joinpath(name) for name in file_names_attached if file_names_attached is not None
            ]
            # suspension_files objects before:
            suspension_files_object_before = await async_db.scalars(select(SuspensionsFiles))  # all suspension_files
            suspension_files_in_db_before = suspension_files_object_before.all()
            object_id_suspension_files_before = await async_db.scalars(
                select(SuspensionsFiles)
                .where(SuspensionsFiles.suspension_id == suspension_id)
            )
            object_id_suspension_files_before_all = object_id_suspension_files_before.all()  # susp-n_files object_id
            # starting test scenarios:
            login_user_response = await ac.post(LOGIN, data=login)
            response = await ac.patch(
                test_url + f"{suspension_id}",
                params=create_params,
                headers={"Authorization": f"Bearer {login_user_response.json()['access_token']}"},
                files=uploaded_file
            )
            assert response.status_code == status, f"{login} couldn't get {test_url}. Response: {response.__dict__}"
            if response.status_code != 200:
                await log.ainfo(
                    f"SCENARIO: _{scenario_number}_ info: {name}",
                    login_data=login,
                    orm_before_patched={
                        "files_attached_before": attached_files_paths_before,
                        "orm_description": object_before_to_patch.description,
                        "orm_start": object_before_to_patch.suspension_start.strftime(DATE_TIME_FORMAT),
                        "orm_finish": object_before_to_patch.suspension_finish.strftime(DATE_TIME_FORMAT),
                        "duration": (
                                object_before_to_patch.suspension_finish
                                - object_before_to_patch.suspension_start
                        ),
                        "suspension_files": suspension_files_in_db_before,
                    },
                    params=create_params,
                    response=response.json(),
                    status=response.status_code,
                    wings_of_end=f"STATUS: {response.status_code}___ END of SCENARIO: ___ {scenario_number}  _{name}_"
                )
                continue
            # patched suspension:
            current_user = await async_db.scalar(select(User).where(User.email == login.get("username")))
            objects = await async_db.scalars(select(Suspension))
            objects_in_db = objects.all()
            object_in_db = [_ for _ in objects_in_db if _.id == suspension_id][0]
            # attached files:
            attached_files_objects = await async_db.scalars(
                select(FileAttached)
                .join(Suspension.files)
                .where(Suspension.id == suspension_id)
            )
            attached_files_in_db = attached_files_objects.all()
            file_names_attached = [file.name for file in attached_files_in_db]
            all_files_in_folder = [file.name for file in FILES_DIR.glob('*')]
            files_in_response = response.json().get(FILES_SET_TO)
            new_file_name_in_response = [
                file for file in files_in_response if file.split("_")[-1] == test_files[file_index]
            ]
            new_file_object = [file for file in attached_files_in_db if file.name == new_file_name_in_response[0]]
            # patched files relations:
            suspension_files_object = await async_db.scalars(select(SuspensionsFiles))
            suspension_files_in_db = suspension_files_object.all()
            if uploaded_file and (create_params.get(FILES_UNLINK) is not True):
                suspension_files_expected = [str(record) for record in suspension_files_in_db_before]
                # get file_id by its name, and make '<Suspinsion 3 - Files 1>' в suspension_files_expected
                suspension_files_expected.append(f'<Suspension {suspension_id} - Files {new_file_object[0].id}>')
                file_names_attached_expected = file_names_attached
                file_names_attached_expected.append(new_file_name_in_response[0])
            elif create_params.get(FILES_UNLINK):
                file_names_attached_expected = []
                suspension_files_expected = [record for record in suspension_files_in_db_before]
                suspension_files_expected = set(
                    suspension_files_expected
                ).difference(set(object_id_suspension_files_before_all))  # delete suspension_files for suspension_id
            else:
                file_names_attached_expected = file_names_attached_before
                suspension_files_expected = suspension_files_in_db_before
            expected = {
                "total_suspensions_expected": len(objects_in_db_before),
                "suspension_expected_id": suspension_id,
                "start": (
                    create_params.get(ANALYTICS_START) if create_params.get(ANALYTICS_START) is not None
                    else object_before_to_patch.suspension_start.strftime(DATE_TIME_FORMAT)
                ),
                "finish": (
                    create_params.get(ANALYTICS_FINISH) if create_params.get(ANALYTICS_FINISH) is not None
                    else object_before_to_patch.suspension_finish.strftime(DATE_TIME_FORMAT)
                ),
                "description": (
                    create_params.get(SUSPENSION_DESCRIPTION) if create_params.get(SUSPENSION_DESCRIPTION) is not None
                    else object_before_to_patch.description
                ),
                "measures": (
                    create_params.get(IMPLEMENTING_MEASURES) if create_params.get(IMPLEMENTING_MEASURES) is not None
                    else object_before_to_patch.implementing_measures
                ),
                "risk_accident": (
                    create_params.get(RISK_ACCIDENT_SOURCE) if create_params.get(RISK_ACCIDENT_SOURCE) is not None
                    else object_before_to_patch.risk_accident
                ),
                "tech_process": (
                    create_params.get(TECH_PROCESS) if create_params.get(TECH_PROCESS) is not None
                    else object_before_to_patch.tech_process
                ),
                "user_id": current_user.id,
                "files_attached": file_names_attached_expected,  # загружаемый + имеющийся в БД
                "suspension_files": [str(record) for record in suspension_files_expected],
            }
            # run asserts in a scenario:
            match_values = (
                # name_value, expected_value, exist_value
                ("Suspension id: ", expected.get("suspension_expected_id"), object_in_db.id),
                ("Total suspensions: ", expected.get("total_suspensions_expected"), len(objects_in_db)),
                ("Attached files: ", expected.get("files_attached"), file_names_attached),
                (
                    "Suspension files: ",
                    set(expected.get("suspension_files")),
                    set([str(record) for record in suspension_files_in_db])
                ),
                (
                    "Suspension start: ",
                    expected.get("start"),
                    object_in_db.suspension_start.strftime(DATE_TIME_FORMAT)
                ),
                (
                    "Suspension finish: ",
                    expected.get("finish"),
                    object_in_db.suspension_finish.strftime(DATE_TIME_FORMAT)
                ),
                ("Description: ", expected.get("description"), object_in_db.description),
                ("Implementing measures: ", expected.get("measures"), object_in_db.implementing_measures),
                ("Risk accident: ", expected.get("risk_accident"), object_in_db.risk_accident),
                ("Tech_process: ", int(expected.get("tech_process")), object_in_db.tech_process),
                (
                    "Duration: ",
                    (
                            datetime.strptime(expected["finish"], DATE_TIME_FORMAT)
                            - datetime.strptime(expected["start"], DATE_TIME_FORMAT)
                    ),
                    object_in_db.suspension_finish - object_in_db.suspension_start
                ),
                ("user_id: ", expected.get("user_id"), object_in_db.user_id),
            )
            for name_value, expected_value, exist_value in match_values:
                assert expected_value == exist_value, f"{name_value} {exist_value} not as expected: {expected_value}"
            if files_in_response is not None:
                for file in files_in_response:
                    assert file in all_files_in_folder, f"Can't find: {file} in files folder: {FILES_DIR}"
            if create_params.get(FILES_UNLINK) is True and attached_files_paths_before:
                for file in attached_files_paths_before:
                    assert file.name not in all_files_in_folder, f"File: {file} is not deleted in folder: {FILES_DIR}"
            await log.ainfo(
                f"SCENARIO: _{scenario_number}_ info: {name}",
                file_name_in_response_new=new_file_name_in_response,
                files_in_response=files_in_response,
                login_data=login,
                orm_before_patched={
                    "files_attached_before": attached_files_paths_before,
                    "orm_start": object_before_to_patch.suspension_start.strftime(DATE_TIME_FORMAT),
                    "orm_finish": object_before_to_patch.suspension_finish.strftime(DATE_TIME_FORMAT),
                    "duration": (
                            object_before_to_patch.suspension_finish
                            - object_before_to_patch.suspension_start
                    ),
                    "suspension_files": suspension_files_in_db_before,
                },
                params=create_params,
                response=response.json(),
                suspension_files_in_db=suspension_files_in_db,
                wings_of_end=f"_______________________________________________ END of SCENARIO: ___ {scenario_number}"
            )
    # if files are not deleted in folder - it means, that scenario of "files unlink" doesn't work correctly
    await clean_test_database(async_db, User, Suspension, FileAttached, SuspensionsFiles)  # files are deleted in api


async def test_user_post_suspension_with_files_form_url(
        async_client: AsyncClient,
        async_db: AsyncSession,
        user_orm: User,
) -> None:
    """
    Тестирует фиксацию случая простоя из формы с обязательной загрузкой нескольких файлов:
    pytest -k test_user_post_suspension_with_files_form_url -vs

    scenarios - тестовые сценарии использования эндпоинта (сценарии изолированы).
    expected - словарь ожидаемых значений в сценарии.
    match_values - кортеж параметров, используемых в assert (ожидание - реальность).
    """
    test_url = SUSPENSIONS_PATH + POST_SUSPENSION_FILES_FORM  # /api/suspensions/post_suspension_with_files_form
    user_orm_login = {"username": "user_fixture@f.com", "password": "testings"}
    now = datetime.now(TZINFO).strftime(DATE_TIME_FORMAT)
    day_ago = (datetime.now(TZINFO) - timedelta(days=1)).strftime(DATE_TIME_FORMAT)
    error_in_date = "11-07-20244: 18:45"
    error_in_time = "11-07-2024: 45:18"
    test_files = ["testfile.txt", "testfile2.txt", "testfile3.txt"]
    await create_test_files(test_files)
    files = [
        ("files_to_upload", open(TEST_ROUTES_DIR.joinpath(test_files[0]), "rb")),
        ("files_to_upload", open(TEST_ROUTES_DIR.joinpath(test_files[1]), "rb")),
        ("files_to_upload", open(TEST_ROUTES_DIR.joinpath(test_files[2]), "rb"))
    ]
    scenario_number = 0
    scenarios = (
        # login, params, status, files, name  # TODO NOT ENOUGH SCENARIOS - add all from test_user_post_task_form_url
        (user_orm_login, {
            ANALYTICS_START: error_in_time,
            ANALYTICS_FINISH: day_ago,
            SUSPENSION_DESCRIPTION: "error_in_time",
            IMPLEMENTING_MEASURES: "test_measures",
            TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
            RISK_ACCIDENT_SOURCE: json.loads(settings.RISK_SOURCE)["ANOTHER"]
        }, 422, files, "error_in_time"),  # 1
        (user_orm_login, {
            ANALYTICS_START: now,
            ANALYTICS_FINISH: error_in_date,
            SUSPENSION_DESCRIPTION: "error_in_date",
            IMPLEMENTING_MEASURES: "test_measures",
            TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
            RISK_ACCIDENT_SOURCE: json.loads(settings.RISK_SOURCE)["ANOTHER"]
        }, 422, files, "error_in_date"),  # 2
        (user_orm_login, {
            ANALYTICS_START: now,
            ANALYTICS_FINISH: day_ago,
            SUSPENSION_DESCRIPTION: "L > R",
            IMPLEMENTING_MEASURES: "test_measures",
            TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
            RISK_ACCIDENT_SOURCE: json.loads(settings.RISK_SOURCE)["ANOTHER"]
        }, 422, files, "L > R"),  # 3
        (user_orm_login, {
            ANALYTICS_START: day_ago,
            ANALYTICS_FINISH: now,
            SUSPENSION_DESCRIPTION: "no files to upload - None",
            IMPLEMENTING_MEASURES: "test_measures",
            TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
            RISK_ACCIDENT_SOURCE: json.loads(settings.RISK_SOURCE)["ANOTHER"]
        }, 422, None, "no files to upload"),  # 4
        (user_orm_login, {
            ANALYTICS_START: day_ago,
            ANALYTICS_FINISH: now,
            SUSPENSION_DESCRIPTION: "no files to upload - []",
            IMPLEMENTING_MEASURES: "test_measures",
            TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
            RISK_ACCIDENT_SOURCE: json.loads(settings.RISK_SOURCE)["ANOTHER"]
        }, 422, [], "no files to upload"),  # 5
        (user_orm_login, {
            ANALYTICS_START: day_ago,
            ANALYTICS_FINISH: now,
            SUSPENSION_DESCRIPTION: "with files",
            IMPLEMENTING_MEASURES: "test_measures",
            TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
            RISK_ACCIDENT_SOURCE: json.loads(settings.RISK_SOURCE)["ANOTHER"]
        }, 200, files, "with files"),  # 6
    )
    async with async_client as ac:
        # !!!! starting testing scenarios:
        for login, create_params, status, files, name in scenarios:
            scenario_number += 1
            await log.ainfo(f"**************************************  SCENARIO: __ {scenario_number} __: {name}")
            login_user_response = await ac.post(LOGIN, data=login)
            response = await ac.post(
                test_url,
                params=create_params,
                headers={"Authorization": f"Bearer {login_user_response.json()['access_token']}"},
                files=files
            )
            assert response.status_code == status, f"{login} couldn't get {test_url}. Response: {response.__dict__}"
            if response.status_code != 200:
                await log.ainfo(
                    f"SCENARIO: _{scenario_number}_ info: ",
                    login_data=login,
                    params=create_params,
                    response=response.json(),
                    status=response.status_code,
                    wings_of_end=f"STATUS: {response.status_code}___ END of SCENARIO: ___ {scenario_number} ___ {name}"
                )
                continue
            # created suspensions:
            objects = await async_db.scalars(select(Suspension))
            objects_in_db = objects.all()
            new_object = objects_in_db[0] if objects_in_db is not None else None
            # created files relations:
            suspension_files_object = await async_db.scalars(select(SuspensionsFiles))
            suspension_files_in_db = suspension_files_object.all()
            suspension_files_records = set(
                ((record.suspension_id, record.file_id) for record in suspension_files_in_db)
            )
            total_suspensions = len(objects_in_db) if objects_in_db is not None else None
            # files attached:
            file_objects = await async_db.scalars(select(FileAttached))
            files_in_db = file_objects.all()
            files_in_response = response.json().get(FILES_SET_TO)
            all_files_in_folder = [file.name for file in FILES_DIR.glob('*')]
            file_paths = [
                FILES_DIR.joinpath(file_name) for file_name in files_in_response if files_in_response is not None
            ]
            expected = {
                "total_suspensions_expected": 1,
                "suspensions_expected_id": response.json()["id"],
                "files_attached": await get_file_names_for_model_db(async_db, Suspension, new_object.id),
                "suspension_files": set(((response.json()["id"], index[0] + 1) for index in enumerate(test_files))),
                "start": create_params.get(ANALYTICS_START),
                "finish": create_params.get(ANALYTICS_FINISH),
                "description": create_params.get(SUSPENSION_DESCRIPTION),
                "measures": create_params.get(IMPLEMENTING_MEASURES),
                "risk_accident": create_params.get(RISK_ACCIDENT_SOURCE),
                "tech_process": create_params.get(TECH_PROCESS),
                "user_id": user_orm.id,
            }
            # run asserts in a scenario:
            match_values = (
                # name_value, expected_value, exist_value
                ("Suspension id: ", expected.get("suspensions_expected_id"), new_object.id),
                ("Total suspensions: ", expected.get("total_suspensions_expected"), total_suspensions),
                ("Attached files: ", set(expected.get("files_attached")), set(files_in_response)),
                ("Suspension files: ", set(expected.get("suspension_files")), suspension_files_records),
                ("Suspension start: ", expected.get("start"), new_object.suspension_start.strftime(DATE_TIME_FORMAT)),
                (
                    "Suspension finish: ",
                    expected.get("finish"),
                    new_object.suspension_finish.strftime(DATE_TIME_FORMAT)
                ),
                ("Description: ", expected.get("description"), new_object.description),
                ("Implementing measures: ", expected.get("measures"), new_object.implementing_measures),
                ("Risk accident: ", expected.get("risk_accident"), new_object.risk_accident),
                ("Tech_process: ", int(expected.get("tech_process")), new_object.tech_process),
                (
                    "Duration: ",
                    (
                        datetime.strptime(expected["finish"], DATE_TIME_FORMAT)
                        - datetime.strptime(expected["start"], DATE_TIME_FORMAT)
                    ),
                    new_object.suspension_finish - new_object.suspension_start
                ),
                ("user_id: ", expected.get("user_id"), new_object.user_id),
                # (": ",),  # more scenarios
            )
            for name_value, expected_value, exist_value in match_values:
                assert expected_value == exist_value, f"{name_value} {exist_value} not as expected: {expected_value}"
            if files_in_response is not None:
                for file in files_in_response:
                    assert file in all_files_in_folder, f"Can't find: {file} in files folder: {FILES_DIR}"
            await log.awarning(
                f"SCENARIO: _{scenario_number}_ info: {name} ",
                files_attached_expected=expected.get("files_attached"),
                files_in_db=files_in_db,
                files_in_response=files_in_response,
                file_paths=file_paths,
                login_data=login,
                params=create_params,
                response=response.json(),
                suspension_files_records=suspension_files_records,
                suspension_files_expected=expected.get("suspension_files"),
                wings_of_end=f"_________________________ END of SCENARIO: ___ {scenario_number} ___ {name} ___"
            )
            await clean_test_database(async_db, User, Suspension, FileAttached, SuspensionsFiles)
            await delete_files_in_folder(file_paths)


async def test_user_post_suspension_form_url(
        async_client: AsyncClient,
        async_db: AsyncSession,
        user_orm: User,
) -> None:
    """
    Тестирует фиксацию случая простоя из формы с возможностью загрузки 1 файла:
    pytest -k test_user_post_suspension_form_url -vs

    scenarios - тестовые сценарии использования эндпоинта (все сценарии изолированы).
    expected - словарь ожидаемых значений в сценарии.
    match_values - кортеж параметров, используемых в assert (ожидание - реальность).
    """
    test_url = SUSPENSIONS_PATH + POST_SUSPENSION_FORM  # /api/suspensions/post_suspension_form
    user_orm_login = {"username": "user_fixture@f.com", "password": "testings"}
    now = datetime.now(TZINFO).strftime(DATE_TIME_FORMAT)
    day_ago = (datetime.now(TZINFO) - timedelta(days=1)).strftime(DATE_TIME_FORMAT)
    error_in_date = "11-07-20244: 18:45"
    error_in_time = "11-07-2024: 45:18"
    test_files = ["testfile.txt"]
    await create_test_files(test_files)
    file_to_upload = {"file_to_upload": open(TEST_ROUTES_DIR.joinpath(test_files[0]), "rb")}
    scenario_number = 0
    scenarios = (
        # login, params, status, file_to_upload, name
        (user_orm_login, {
            ANALYTICS_START: error_in_time,
            ANALYTICS_FINISH: day_ago,
            SUSPENSION_DESCRIPTION: "error_in_time",
            IMPLEMENTING_MEASURES: "test_measures",
            TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
            RISK_ACCIDENT_SOURCE: json.loads(settings.RISK_SOURCE)["ANOTHER"]
        }, 422, None, "error_in_time"),  # 1
        (user_orm_login, {
            ANALYTICS_START: now,
            ANALYTICS_FINISH: error_in_date,
            SUSPENSION_DESCRIPTION: "error_in_date",
            IMPLEMENTING_MEASURES: "test_measures",
            TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
            RISK_ACCIDENT_SOURCE: json.loads(settings.RISK_SOURCE)["ANOTHER"]
        }, 422, None, "error_in_date"),  # 2
        (user_orm_login, {
            ANALYTICS_START: now,
            ANALYTICS_FINISH: day_ago,
            SUSPENSION_DESCRIPTION: "L > R",
            IMPLEMENTING_MEASURES: "test_measures",
            TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
            RISK_ACCIDENT_SOURCE: json.loads(settings.RISK_SOURCE)["ANOTHER"]
        }, 422, None, "3 L > R"),  # 3
        (user_orm_login, {
            ANALYTICS_START: day_ago,
            ANALYTICS_FINISH: now,
            SUSPENSION_DESCRIPTION: "no files to upload - None",
            IMPLEMENTING_MEASURES: "test_measures",
            TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
            RISK_ACCIDENT_SOURCE: json.loads(settings.RISK_SOURCE)["ANOTHER"]
        }, 200, None, "no files to upload"),  # 4
        (user_orm_login, {
            ANALYTICS_START: day_ago,
            ANALYTICS_FINISH: now,
            SUSPENSION_DESCRIPTION: "with files",
            IMPLEMENTING_MEASURES: "test_measures",
            TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
            RISK_ACCIDENT_SOURCE: json.loads(settings.RISK_SOURCE)["ANOTHER"]
        }, 200, file_to_upload, "with files"),  # 5
    )
    async with async_client as ac:
        # !!!! starting testing scenarios:
        for login, create_params, status, files, name in scenarios:
            scenario_number += 1
            await log.ainfo(f"**************************************  SCENARIO: __ {scenario_number} __: {name}")
            login_user_response = await ac.post(LOGIN, data=login)
            response = await ac.post(
                test_url,
                params=create_params,
                headers={"Authorization": f"Bearer {login_user_response.json()['access_token']}"},
                files=files
            )
            assert response.status_code == status, f"{login} couldn't get {test_url}. Response: {response.__dict__}"
            if response.status_code != 200:
                await log.ainfo(
                    f"SCENARIO: _{scenario_number}___ {name}___ info: ",
                    login_data=login,
                    params=create_params,
                    response=response.json(),
                    status=response.status_code,
                    wings_of_end=f"STATUS: {response.status_code}___ END of SCENARIO: ___ {scenario_number}___ {name}"
                )
                continue
            # created suspensions:
            objects = await async_db.scalars(select(Suspension))
            objects_in_db = objects.all()
            new_object = objects_in_db[0] if objects_in_db is not None else None
            total_suspensions = len(objects_in_db) if objects_in_db is not None else None
            # files attached:
            file_objects = await async_db.scalars(select(FileAttached))
            files_in_db = file_objects.all()
            files_in_response = response.json().get(FILES_SET_TO)
            all_files_in_folder = [file.name for file in FILES_DIR.glob('*')]
            file_paths = [
                FILES_DIR.joinpath(file_name) for file_name in files_in_response if files_in_response is not None
            ]
            # created files relations:
            suspension_files_object = await async_db.scalars(select(SuspensionsFiles))
            suspension_files_in_db = suspension_files_object.all()
            suspension_files_records = set(
                ((record.suspension_id, record.file_id) for record in suspension_files_in_db)
            )
            expected = {
                "total_suspensions_expected": 1,
                "suspensions_expected_id": response.json()["id"],
                "files_attached": await get_file_names_for_model_db(async_db, Suspension, new_object.id),
                "suspension_files": set(
                    ((response.json()["id"], index[0] + 1) for index in enumerate(files_in_response))
                ),  # todo масло масляное по сути files_in_response - обращается к БД, а не к исходникам ожидаемым
                "start": create_params.get(ANALYTICS_START),
                "finish": create_params.get(ANALYTICS_FINISH),
                "description": create_params.get(SUSPENSION_DESCRIPTION),
                "measures": create_params.get(IMPLEMENTING_MEASURES),
                "risk_accident": create_params.get(RISK_ACCIDENT_SOURCE),
                "tech_process": create_params.get(TECH_PROCESS),
                "user_id": user_orm.id,
            }
            # run asserts in a scenario:
            match_values = (
                # name_value, expected_value, exist_value
                ("Suspension id: ", expected.get("suspensions_expected_id"), new_object.id),
                ("Total suspensions: ", expected.get("total_suspensions_expected"), total_suspensions),
                ("Attached files: ", set(expected.get("files_attached")), set(files_in_response)),
                ("Suspension files: ", set(expected.get("suspension_files")), suspension_files_records),
                ("Suspension start: ", expected.get("start"), new_object.suspension_start.strftime(DATE_TIME_FORMAT)),
                (
                    "Suspension finish: ",
                    expected.get("finish"),
                    new_object.suspension_finish.strftime(DATE_TIME_FORMAT)
                ),
                ("Description: ", expected.get("description"), new_object.description),
                ("Implementing measures: ", expected.get("measures"), new_object.implementing_measures),
                ("Risk accident: ", expected.get("risk_accident"), new_object.risk_accident),
                ("Tech_process: ", int(expected.get("tech_process")), new_object.tech_process),
                (
                    "Duration: ",
                    (
                        datetime.strptime(expected["finish"], DATE_TIME_FORMAT)
                        - datetime.strptime(expected["start"], DATE_TIME_FORMAT)
                    ),
                    new_object.suspension_finish - new_object.suspension_start
                ),
                ("user_id: ", expected.get("user_id"), new_object.user_id),
            )
            for name_value, expected_value, exist_value in match_values:
                assert expected_value == exist_value, f"{name_value} {exist_value} not as expected: {expected_value}"
            if files_in_response is not None:
                for file in files_in_response:
                    assert file in all_files_in_folder, f"Can't find: {file} in files folder: {FILES_DIR}"
            await log.awarning(
                f"SCENARIO: _{scenario_number}_ info: {name}",
                files_attached_expected=expected.get("files_attached"),
                files_in_db=files_in_db,
                files_in_response=files_in_response,
                file_paths=file_paths,
                login_data=login,
                params=create_params,
                response=response.json(),
                suspension_files_records=suspension_files_records,
                suspension_files_expected=expected.get("suspension_files"),
                wings_of_end=f"_________ END of SCENARIO: ___ {scenario_number}___ {name}"
            )
            await clean_test_database(async_db, Suspension, FileAttached, SuspensionsFiles)
            await delete_files_in_folder(file_paths)
    await clean_test_database(async_db, User)


async def test_user_get_suspension_url(
        async_client: AsyncClient,
        async_db: AsyncSession,
        suspensions_orm: Suspension,
) -> None:
    """
    Тестирует возможность получения по id информации о случае простоя, или загрузки прикрепленных файлов:
    pytest -k test_user_get_suspension_url -vs

    before_patched - параметры простоя при его создании: тождественны "scenarios" из suspensions_orm в confest.py

    scenarios - тестовые сценарии использования эндпоинта (сценарии не изолированы друг от друга).
    expected - словарь ожидаемых значений в сценарии.
    match_values - кортеж параметров, используемых в assert (ожидание - реальность).

    """
    test_url = SUSPENSIONS_PATH + "/"  # /api/suspensions/{suspension_id}
    user_orm_login = {"username": "user_fixture@f.com", "password": "testings"}
    test_files = ["testfile.txt", "testfile2.txt", "testfile3.txt"]
    await create_test_files(test_files)
    file_to_attach = {"file_to_upload": open(TEST_ROUTES_DIR.joinpath(test_files[0]), "rb")}
    json_choice = [_ for _ in json.loads(settings.CHOICE_DOWNLOAD_FILES).values()][0]  # next(iter())
    files_choice = [_ for _ in json.loads(settings.CHOICE_DOWNLOAD_FILES).values()][1]  # 2nd == "files"
    scenario_number = 0
    scenarios = (
        # login, params, status, uploaded_file, suspension_id, name
        (user_orm_login, {CHOICE_FORMAT: json_choice}, 200, None, 1, "json-choice"),  # 1
        (user_orm_login, {CHOICE_FORMAT: json_choice}, 200, None, 2, "json-choice"),  # 2
        (user_orm_login, {CHOICE_FORMAT: files_choice}, 404, None, 2, "files_choice when no files attached"),  # 3
        (user_orm_login, {CHOICE_FORMAT: json_choice}, 200, file_to_attach, 2, "patch object by adding a file"),  # 4
        (user_orm_login, {CHOICE_FORMAT: json_choice}, 200, file_to_attach, 2, "adding one more file to object"),  # 5
        (user_orm_login, {CHOICE_FORMAT: files_choice}, 200, None, 2, "and now try to get attached files"),  # 6
    )
    async with async_client as ac:
        # !!!! starting testing scenarios:
        for login, params, status, uploaded_file, suspension_id, name in scenarios:
            scenario_number += 1
            await log.ainfo(f"**************************************  SCENARIO: __ {scenario_number} __: {name}")
            # grab info of objects in db before testing:
            objects_before = await async_db.scalars(select(Suspension))  # objects before scenarios have started
            objects_in_db_before = objects_before.all()  # objects before scenarios have started
            object_before_testing = [_ for _ in objects_in_db_before if _.id == suspension_id][0]
            attached_files_objects_before = await async_db.scalars(
                select(FileAttached)
                .join(Suspension.files)
                .where(Suspension.id == suspension_id)
            )
            attached_files_in_db_before = attached_files_objects_before.all()
            attached_files_paths_before = [
                FILES_DIR.joinpath(file.name) for file in attached_files_in_db_before
                if attached_files_in_db_before is not None
            ]
            login_user_response = await ac.post(LOGIN, data=login)
            if uploaded_file is not None:  # adding file to the object_id in order to get this file later
                response_patched = await ac.patch(
                    test_url + f"{suspension_id}",
                    params={SUSPENSION_DESCRIPTION: "suspension is attached with files"},
                    headers={"Authorization": f"Bearer {login_user_response.json()['access_token']}"},
                    files=uploaded_file
                )
                assert response_patched.status_code == status, (
                    f"User: {login} couldn't patch {test_url}. Response: {response.__dict__}"
                )
            response = await ac.get(
                test_url + f"{suspension_id}",
                params=params,
                headers={"Authorization": f"Bearer {login_user_response.json()['access_token']}"},
            )
            assert response.status_code == status, f"{login} couldn't get {test_url}. Response: {response.__dict__}"
            if response.status_code != 200:
                await log.ainfo(
                    f"SCENARIO: _{scenario_number}_ info: {name}",
                    login_data=login,
                    response=response.json(),
                    status=response.status_code,
                    wings_of_end=f"STATUS: {response.status_code}___ END of SCENARIO: ___ {scenario_number}  __{name}"
                )
                continue
            if params.get(CHOICE_FORMAT) == files_choice:
                # checking only file zip_name correct in headers
                zip_name = response.headers.get("content-disposition").split(";")[1].split("=")[1]
                expected_zip_name = FILE_NAME_SAVE_FORMAT + "_archive.zip"
                assert zip_name == expected_zip_name, (
                    f"Chosen file_choice: {files_choice}, but couldn't get {expected_zip_name}. "
                    f"Headers: {response.headers}. Dict: {response.__dict__}"
                )
                await log.ainfo(
                    f"SCENARIO: _{scenario_number}_ files_choice: {name}",
                    login_data=login,
                    headers=response.headers,
                    wings_of_end=f"STATUS: {response.status_code}_ END of SCENARIO: _ {scenario_number}____{name}!!"
                )
                await delete_files_in_folder(file_paths)
                continue
            # suspensions after test running:
            objects = await async_db.scalars(select(Suspension))
            objects_in_db = objects.all()
            object_in_db = [_ for _ in objects_in_db if _.id == suspension_id][0]
            # files after test running:
            files_in_response = response.json().get(FILES_SET_TO)
            file_objects = await async_db.scalars(select(FileAttached))  # == [] when no files attached
            files_in_db = file_objects.all() if file_objects is not None else []
            file_paths = [
                FILES_DIR.joinpath(file_name) for file_name in files_in_response if files_in_response is not None
            ]
            all_files_in_folder = [file.name for file in FILES_DIR.glob('*')]
            # files relations after test running:
            suspension_files_object = await async_db.scalars(select(SuspensionsFiles))
            suspension_files_in_db = suspension_files_object.all()
            suspension_files_records = set(
                ((record.suspension_id, record.file_id) for record in suspension_files_in_db)
            )
            suspension_files_in_scenario = tuple(suspension_files_records)
            expected = {
                "total_expected_before": len(objects_in_db_before),
                "files_attached": await get_file_names_for_model_db(async_db, Suspension, object_before_testing.id),
                "suspension_files": suspension_files_in_scenario,
                "start": object_before_testing.suspension_start,
                "finish": object_before_testing.suspension_finish,
                "description": object_before_testing.description,
                "measures": object_before_testing.implementing_measures,
                "risk_accident": object_before_testing.risk_accident,
                "tech_process": int(object_before_testing.tech_process),
                "user_id": object_before_testing.user_id,
            }
            # run asserts in a scenario:
            match_values = (
                # name_value, expected_value, exist_value
                ("Suspension id: ", suspension_id, object_before_testing.id),
                ("Total suspensions: ", expected.get("total_expected_before"), len(objects_in_db)),
                ("Attached files after: ", set(expected.get("files_attached")), set(files_in_response)),
                ("Suspension files: ", set(expected.get("suspension_files")), suspension_files_records),
                ("Suspension start: ", expected.get("start"), object_in_db.suspension_start),
                ("Suspension finish: ", expected.get("finish"), object_in_db.suspension_finish),
                ("Description: ", expected.get("description"), object_in_db.description),
                ("Implementing measures: ", expected.get("measures"), object_in_db.implementing_measures),
                ("Risk accident: ", expected.get("risk_accident"), object_in_db.risk_accident),
                (
                    "Tech process: ",
                    expected.get("tech_process"),
                    int(json.loads(settings.TECH_PROCESS).get(response.json().get(TECH_PROCESS)))
                ),
                (
                    "Duration: ",
                    (
                        (object_before_testing.suspension_finish
                            - object_before_testing.suspension_start).total_seconds() / SUSPENSION_DURATION_RESPONSE
                    ),
                    response.json().get(SUSPENSION_DURATION)
                ),
                ("user_id: ", expected.get("user_id"), object_in_db.user_id),
            )
            for name_value, expected_value, exist_value in match_values:
                assert expected_value == exist_value, f"{name_value} {exist_value} not as expected: {expected_value}"
            if files_in_response is not None:
                for file in files_in_response:
                    assert file in all_files_in_folder, f"Can't find: {file} in files folder: {FILES_DIR}"
            await log.ainfo(
                f"SCENARIO: _{scenario_number}_ info: {name}",
                files_attached_before=attached_files_paths_before,
                files_attached_expected=expected.get("files_attached"),
                files_in_db=files_in_db,
                files_in_response=files_in_response,
                file_paths=file_paths,
                login_data=login,
                params=params,
                response=response.json(),
                suspension_files_expected=set(expected.get("suspension_files")),
                wings_of_end=f"______________ END of SCENARIO: ___ {scenario_number} ____ __{name} _______"
            )
    await delete_files_in_folder(file_paths)
    await clean_test_database(async_db, User, Suspension, FileAttached, SuspensionsFiles)


async def test_user_get_all_suspension_url(
        async_client: AsyncClient,
        async_db: AsyncSession,
        suspensions_orm: Suspension,
) -> None:
    """
    Тестирует возможность получения всех случаев простоя:
    pytest -k test_user_get_all_suspension_url -vs

    before_patched - параметры простоя при его создании: тождественны "scenarios" из suspensions_orm в confest.py

    scenarios - тестовые сценарии использования эндпоинта (сценарии не изолированы друг от друга).
    expected - словарь ожидаемых значений в сценарии.
    match_values - кортеж параметров, используемых в assert (ожидание - реальность).

    """
    test_url = SUSPENSIONS_PATH + MAIN_ROUTE  # /api/suspensions/
    user_orm_login = {"username": "user_fixture@f.com", "password": "testings"}
    scenario_number = 0
    scenarios = (
        # login, status, name
        (user_orm_login, 200, "get_all"),  # 1
    )
    async with async_client as ac:
        # !!!! starting testing scenarios:
        for login, status, name in scenarios:
            scenario_number += 1
            await log.ainfo(f"**************************************  SCENARIO: __ {scenario_number} __: {name}")
            login_user_response = await ac.post(LOGIN, data=login)
            response = await ac.get(
                test_url,
                headers={"Authorization": f"Bearer {login_user_response.json()['access_token']}"},
            )
            assert response.status_code == status, f"{login} couldn't get {test_url}. Response: {response.__dict__}"
            if response.status_code != 200:
                await log.ainfo(
                    f"SCENARIO: _{scenario_number}_ info: {name}",
                    login_data=login,
                    response=response.json(),
                    status=response.status_code,
                    wings_of_end=f"STATUS: {response.status_code}___ END of SCENARIO: ___ {scenario_number}  __{name}"
                )
                continue
            for index in enumerate(suspensions_orm):  # проводим сверки по каждому объекту фикстуры и в ответе response
                position = index[0] + 1
                fixture_object = [_ for _ in suspensions_orm if _.id == position][0]
                object_in_response = [_ for _ in response.json() if _["id"] == position][0]
                expected = {
                    "total_objects": len(suspensions_orm),
                    "suspension_files": [],
                    "start": fixture_object.suspension_start.strftime(DATE_TIME_FORMAT),
                    "finish": fixture_object.suspension_finish.strftime(DATE_TIME_FORMAT),
                    "description": fixture_object.description,
                    "measures": fixture_object.implementing_measures,
                    "risk_accident": fixture_object.risk_accident,
                    "tech_process": int(fixture_object.tech_process),
                    "user_id": fixture_object.user_id,
                }
                # run asserts in a scenario:
                match_values = (
                    # name_value, expected_value, exist_value
                    ("Total suspensions: ", expected.get("total_objects"), len(response.json())),
                    ("Suspension files: ", expected.get("suspension_files"), object_in_response[FILES_SET_TO]),
                    ("Suspension start: ", expected.get("start"), object_in_response[SUSPENSION_START]),
                    ("Suspension finish: ", expected.get("finish"), object_in_response[SUSPENSION_FINISH]),
                    ("Description: ", expected.get("description"), object_in_response[SUSPENSION_DESCRIPTION]),
                    ("Implementing measures: ", expected.get("measures"), object_in_response[IMPLEMENTING_MEASURES]),
                    ("Risk accident: ", expected.get("risk_accident"), object_in_response[RISK_ACCIDENT]),
                    (
                        "Tech process: ",
                        expected.get("tech_process"),
                        int(json.loads(settings.TECH_PROCESS).get(object_in_response.get(TECH_PROCESS)))
                    ),
                    (
                        "Duration: ",
                        (
                            (fixture_object.suspension_finish
                                - fixture_object.suspension_start).total_seconds() / SUSPENSION_DURATION_RESPONSE
                        ),
                        object_in_response.get(SUSPENSION_DURATION)
                    ),
                    ("user_id: ", expected.get("user_id"), object_in_response[USER_ID]),
                )
                for name_value, expected_value, exist_value in match_values:
                    assert expected_value == exist_value, (
                        f"{name_value} {exist_value} not as expected: {expected_value}"
                    )
            await log.ainfo(
                f"SCENARIO: _{scenario_number}_ info: {name}",
                login_data=login,
                response=response.json(),
                wings_of_end=f"______________ END of SCENARIO: ___ {scenario_number} ____ __{name} _______"
            )
    await clean_test_database(async_db, User, Suspension, FileAttached, SuspensionsFiles)


async def test_user_get_my_suspension_url(
        async_client: AsyncClient,
        async_db: AsyncSession,
        suspensions_orm: Suspension,
) -> None:
    """
    Тестирует возможность получения всех случаев простоя:
    pytest -k test_user_get_my_suspension_url -vs

    before_patched - параметры простоя при его создании: тождественны "scenarios" из suspensions_orm в confest.py

    scenarios - тестовые сценарии использования эндпоинта (сценарии не изолированы друг от друга).
    expected - словарь ожидаемых значений в сценарии.
    match_values - кортеж параметров, используемых в assert (ожидание - реальность).

    """
    test_url = SUSPENSIONS_PATH + MY_SUSPENSIONS  # /api/suspensions/my_suspensions
    user_orm_login = {"username": "user_fixture@f.com", "password": "testings"}
    user_settings_email = json.loads(settings.STAFF)["1"]
    user_settings_login = {"username": user_settings_email, "password": "testings"}
    scenario_number = 0
    scenarios = (
        # login, status, name
        (user_orm_login, 200, "get_user_orm_suspensions"),  # 1
        (user_settings_login, 200, "get_user_settings_suspensions"),  # 2
    )
    async with async_client as ac:
        # !!!! starting testing scenarios:
        for login, status, name in scenarios:
            scenario_number += 1
            await log.ainfo(f"**************************************  SCENARIO: __ {scenario_number} __: {name}")
            login_user_response = await ac.post(LOGIN, data=login)
            response = await ac.get(
                test_url,
                headers={"Authorization": f"Bearer {login_user_response.json()['access_token']}"},
            )
            assert response.status_code == status, f"{login} couldn't get {test_url}. Response: {response.__dict__}"
            if response.status_code != 200:
                await log.ainfo(
                    f"SCENARIO: _{scenario_number}_ info: {name}",
                    login_data=login,
                    response=response.json(),
                    status=response.status_code,
                    wings_of_end=f"STATUS: {response.status_code}___ END of SCENARIO: ___ {scenario_number}  __{name}"
                )
                continue
            current_user = await async_db.scalar(select(User).where(User.email == login.get("username")))
            objects_by_user = await async_db.scalars(select(Suspension).where(Suspension.user_id == current_user.id))
            objects_by_user_in_db = objects_by_user.all()
            for user_object in objects_by_user_in_db:
                object_in_response = [_ for _ in response.json() if _["id"] == user_object.id][0]
                expected = {
                    "total_objects": len(objects_by_user_in_db),
                    "suspension_files": [],
                    "start": user_object.suspension_start.strftime(DATE_TIME_FORMAT),
                    "finish": user_object.suspension_finish.strftime(DATE_TIME_FORMAT),
                    "description": user_object.description,
                    "measures": user_object.implementing_measures,
                    "risk_accident": user_object.risk_accident,
                    "tech_process": int(user_object.tech_process),
                    "user_id": user_object.user_id,
                }
            # run asserts in a scenario:
                match_values = (
                    # name_value, expected_value, exist_value
                    ("Total suspensions: ", expected.get("total_objects"), len(response.json())),
                    # ("Suspension files: ", expected.get("suspension_files"), object_in_response[FILES_SET_TO]),
                    ("Suspension start: ", expected.get("start"), object_in_response[SUSPENSION_START]),
                    ("Suspension finish: ", expected.get("finish"), object_in_response[SUSPENSION_FINISH]),
                    ("Description: ", expected.get("description"), object_in_response[SUSPENSION_DESCRIPTION]),
                    ("Implementing measures: ", expected.get("measures"), object_in_response[IMPLEMENTING_MEASURES]),
                    ("Risk accident: ", expected.get("risk_accident"), object_in_response[RISK_ACCIDENT]),
                    (
                        "Tech process: ",
                        expected.get("tech_process"),
                        int(json.loads(settings.TECH_PROCESS).get(object_in_response.get(TECH_PROCESS)))
                    ),
                    (
                        "Duration: ",
                        round(
                            (user_object.suspension_finish
                                - user_object.suspension_start).total_seconds() / SUSPENSION_DURATION_RESPONSE, 1
                        ),
                        round(object_in_response.get(SUSPENSION_DURATION), 1)
                    ),
                    ("user_id: ", expected.get("user_id"), object_in_response[USER_ID]),
                )
                for name_value, expected_value, exist_value in match_values:
                    assert expected_value == exist_value, (
                        f"{name_value} {exist_value} not as expected: {expected_value}"
                    )
            await log.ainfo(
                f"SCENARIO: _{scenario_number}_ info: {name}",
                login_data=login,
                response=response.json(),
                wings_of_end=f"______________ END of SCENARIO: ___ {scenario_number} ____ __{name} _______"
            )
    await clean_test_database(async_db, User, Suspension, FileAttached, SuspensionsFiles)


async def test_super_user_add_files_to_suspension_url(
        async_client: AsyncClient,
        async_db: AsyncSession,
        suspensions_orm: Suspension,
        super_user_orm: User
) -> None:
    """
    Тестирует добавление супер-пользователем к случаю простоя id файлов из формы:
    pytest -k test_super_user_add_files_to_suspension_url -vs

    before_patched - параметры простоя при его создании: тождественны "scenarios" из suspensions_orm в confest.py

    scenarios - тестовые сценарии использования эндпоинта (сценарии не изолированы друг от друга).
    expected - словарь ожидаемых значений в сценарии.
    match_values - кортеж параметров, используемых в assert (ожидание - реальность).

    """
    test_url = SUSPENSIONS_PATH + ADD_FILES_TO_SUSPENSION  # /api/suspensions/add_files_to_suspension
    download_files_url = FILES_PATH + DOWNLOAD_FILES  # /api/files/download_files
    user_orm_login = {"username": "user_fixture@f.com", "password": "testings"}
    super_user_login = {"username": super_user_orm.email, "password": "testings"}
    test_files = ["testfile.txt", "testfile2.txt", "testfile3.txt"]
    await create_test_files(test_files)
    files_to_delete_at_the_end = []
    scenario_number = 0
    scenarios = (
        # login, params, status, file_index, name - Dependant scenarios !!!
        (user_orm_login, {'suspension_id': 1, SET_FILES_LIST_TO_SUSPENSION: [1]}, 403, 0, "obj_1 not admin"),  # 1
        (super_user_login, {'suspension_id': 1, SET_FILES_LIST_TO_SUSPENSION: [1]}, 200, 0, "obj_1 add fle_id 1"),  # 2
        (super_user_login, {'suspension_id': 1, SET_FILES_LIST_TO_SUSPENSION: [2]}, 200, 1, "obj_1 add f_id 2"),  # 3
        (super_user_login, {'suspension_id': 1, SET_FILES_LIST_TO_SUSPENSION: [1, 2]}, 200, 2, "obj_1 fls: 1,2"),  # 4
        (super_user_login, {'suspension_id': 2, SET_FILES_LIST_TO_SUSPENSION: [1, 2, 3]}, 200, 2, "obj_2 fls: 1,2,3"),
        (super_user_login, {'suspension_id': 3, SET_FILES_LIST_TO_SUSPENSION: [1, 2, 3, 4, 5]}, 200, 2, "obj_3 5 fls"),
    )
    async with async_client as ac:
        # !!!! starting testing scenarios:
        for login, create_params, status, file_index, name in scenarios:
            scenario_number += 1
            await log.ainfo(f"**************************************  SCENARIO: __ {scenario_number} __: {name}")
            # grab objects in db info before testing:
            suspension_id = create_params.get('suspension_id')
            suspension_files_object_before = await async_db.scalars(select(SuspensionsFiles))
            suspension_files_in_db_before = suspension_files_object_before.all()
            object_id_suspension_files_before = await async_db.scalars(
                select(SuspensionsFiles)
                .where(SuspensionsFiles.suspension_id == suspension_id)
            )
            object_id_suspension_files_before_all = object_id_suspension_files_before.all()  # susp._files to obj_id
            login_super_user_response = await ac.post(LOGIN, data=super_user_login)  # only super_user is allowed!
            assert login_super_user_response.status_code == 200, f"Super_user: {super_user_login} can't get {LOGIN}"
            # downloading files with api to test it in scenarios
            download_files_response = await ac.post(
                download_files_url,
                files={"files": open(TEST_ROUTES_DIR.joinpath(test_files[file_index]), "rb")},
                headers={"Authorization": f"Bearer {login_super_user_response.json()['access_token']}"},
            )
            assert download_files_response.status_code == 200, (
                f"User: {super_user_login} can't get {download_files_url} Response: {download_files_response.__dict__}"
            )
            file_objects = await async_db.scalars(select(FileAttached))
            files_in_db = file_objects.all()
            files_downloaded_response = download_files_response.json().get(FILES_WRITTEN_DB)
            file_names_added = [file_dict.get(FILE_NAME) for file_dict in files_downloaded_response]
            file_paths = [
                FILES_DIR.joinpath(file_name) for file_name in file_names_added if file_names_added is not None
            ]
            login_user_response = await ac.post(LOGIN, data=login)  # files are attached, so tests could be started
            response = await ac.post(
                test_url,
                params=create_params,
                headers={"Authorization": f"Bearer {login_user_response.json()['access_token']}"},
            )
            assert response.status_code == status, f"User: {login} can't get {test_url}. Response: {response.__dict__}"
            if response.status_code != 200:
                await log.ainfo(
                    f"SCENARIO: ___ status_code != 200___ _{scenario_number}_ info: {name}",
                    files_in_db=files_in_db,
                    login_data=login,
                    params=create_params,
                    response=response.json(),
                    status=response.status_code,
                    wings_of_end=f"STATUS: {response.status_code}___ END of SCENARIO: ___ {scenario_number}  _{name}_"
                )
                await delete_files_in_folder(file_paths)
                await clean_test_database(async_db, FileAttached)  # clean data after failed scenario
                continue
            # patched suspensions:
            objects = await async_db.scalars(select(Suspension))
            objects_in_db = objects.all()
            object_in_db = [_ for _ in objects_in_db if _.id == suspension_id][0]
            # patched files:
            attached_files_objects = await async_db.scalars(
                select(FileAttached)
                .join(Suspension.files)
                .where(Suspension.id == suspension_id)
            )
            attached_files_in_db = attached_files_objects.all()
            file_names_attached = [file.name for file in attached_files_in_db]
            all_files_in_folder = [file.name for file in FILES_DIR.glob('*')]
            files_by_ids_in_db = await async_db.scalars(
                select(FileAttached).where(FileAttached.id.in_(create_params.get(SET_FILES_LIST_TO_SUSPENSION)))
            )
            files_by_ids_in_db_all = files_by_ids_in_db.all()
            file_names_get_by_set_ids = [file.name for file in files_by_ids_in_db_all]
            file_objects = await async_db.scalars(select(FileAttached))  # == [] when no files attached
            files_in_db = file_objects.all() if file_objects is not None else []
            files_to_delete_at_the_end += file_paths
            # suspension_files:
            suspension_files_object = await async_db.scalars(select(SuspensionsFiles))
            suspension_files_in_db = suspension_files_object.all()
            suspension_files_expected = (
                set(suspension_files_in_db_before).difference(set(object_id_suspension_files_before_all))
            )
            suspension_files_expected = list(suspension_files_expected)
            for file_id in create_params.get(SET_FILES_LIST_TO_SUSPENSION):
                suspension_files_expected.append(f'<Suspension {suspension_id} - Files {file_id}>')
            expected = {
                "files_attached": file_names_get_by_set_ids,
                "suspension_files": [str(record) for record in suspension_files_expected],
            }
            match_values = (
                # name_value, expected_value, exist_value
                ("Suspension id: ", suspension_id, object_in_db.id),
                ("Attached files: ", set(expected.get("files_attached")), set(file_names_attached)),
                (
                    "Suspension files: ",
                    set(expected.get("suspension_files")),
                    set([str(record) for record in suspension_files_in_db])
                ),
            )
            for name_value, expected_value, exist_value in match_values:
                assert expected_value == exist_value, f"{name_value} {exist_value} not as expected: {expected_value}"
            if file_names_added is not None:
                for file in file_names_added:
                    assert file in all_files_in_folder, f"Can't find: {file} in files folder: {FILES_DIR}"
            await log.ainfo(
                f"SCENARIO: _{scenario_number}_ info: {name}",
                all_files_in_db=files_in_db,
                file_names_attached_to_suspension=file_names_attached,
                file_names_downloaded=file_names_added,
                file_names_get_by_set_ids=file_names_get_by_set_ids,
                login_data=login,
                params=create_params,
                response=response.json(),
                suspension_files_in_db_before=suspension_files_in_db_before,
                suspension_files_in_db=suspension_files_in_db,
                wings_of_end=f"_______________________________________________ END of SCENARIO: ___ {scenario_number}"
            )
    await clean_test_database(async_db, User, Suspension, FileAttached, SuspensionsFiles)
    await delete_files_in_folder(files_to_delete_at_the_end)


async def test_super_user_delete_suspension_url(
        async_client: AsyncClient,
        async_db: AsyncSession,
        suspensions_orm: Suspension,
        super_user_orm: User
) -> None:
    """
    Тестирует удаление супер-пользователем случая простоя по id из формы:
    pytest -k test_super_user_delete_suspension_url -vs

    before_patched - параметры простоя при его создании: тождественны "scenarios" из suspensions_orm в confest.py

    scenarios - тестовые сценарии редактирования простоев (сценарии не изолированы друг от друга).
    expected - словарь ожидаемых значений в сценарии.
    match_values - кортеж параметров, используемых в assert (ожидание - реальность).

    """
    test_url = SUSPENSIONS_PATH + "/"  # /api/suspensions/{suspension_id}
    download_files_url = FILES_PATH + DOWNLOAD_FILES  # /api/files/download_files
    user_orm_login = {"username": "user_fixture@f.com", "password": "testings"}
    super_user_login = {"username": super_user_orm.email, "password": "testings"}
    test_files = ["testfile.txt", "testfile2.txt", "testfile3.txt"]
    files_list_set_to_suspension = [1]
    await create_test_files(test_files)
    scenario_number = 0
    files_to_delete_at_the_end = []
    scenarios = (
        # login, params, status, file_index, name, add_file_to_suspension_id
        (user_orm_login, {'suspension_id': 1}, 403, 0, "obj_1 not admin", 1),  # 1
        (super_user_login, {'suspension_id': 1}, 200, 0, "delete obj_1", 1),  # 2
        (super_user_login, {'suspension_id': 1}, 404, 0, "can't delete obj_1 again", 2),  # 3
        (super_user_login, {'suspension_id': 2}, 200, 0, "delete obj_2 with 2 files", 2),  # 4
    )
    async with async_client as ac:
        # !!!! starting testing scenarios:
        for login, create_params, status, file_index, name, add_file_to_suspension_id in scenarios:
            scenario_number += 1
            await log.ainfo(f"**************************************  SCENARIO: __ {scenario_number} __: {name}")
            # grab objects in db info before testing:
            suspension_id = create_params.get('suspension_id')
            suspension_files_object_before = await async_db.scalars(select(SuspensionsFiles))
            suspension_files_in_db_before = suspension_files_object_before.all()
            login_super_user_response = await ac.post(LOGIN, data=super_user_login)  # only super_user is allowed!
            assert login_super_user_response.status_code == 200, f"Super_user: {super_user_login} can't get {LOGIN}"
            # DOWNLOAD files with api to test removing files along with suspension
            download_files_response = await ac.post(
                download_files_url,
                files={"files": open(TEST_ROUTES_DIR.joinpath(test_files[file_index]), "rb")},
                headers={"Authorization": f"Bearer {login_super_user_response.json()['access_token']}"},
            )
            assert download_files_response.status_code == 200, (
                f"User: {super_user_login} can't get {download_files_url} Response: {download_files_response.__dict__}"
            )
            set_files_response = await ac.post(
                SUSPENSIONS_PATH + ADD_FILES_TO_SUSPENSION,
                params={
                    'suspension_id': add_file_to_suspension_id,
                    SET_FILES_LIST_TO_SUSPENSION: files_list_set_to_suspension
                },
                headers={"Authorization": f"Bearer {login_super_user_response.json()['access_token']}"},
            )
            assert set_files_response.status_code == 200, (
                f"User: {login} can't get {test_url}. Response: {set_files_response.__dict__}"
            )
            files_downloaded_response = download_files_response.json().get(FILES_WRITTEN_DB)
            file_names_added = [file_dict.get(FILE_NAME) for file_dict in files_downloaded_response]
            all_files_in_folder = [file.name for file in FILES_DIR.glob('*')]
            if file_names_added is not None:
                for file in file_names_added:
                    assert file in all_files_in_folder, f"Can't find: {file} in files folder: {FILES_DIR}"
            # START TESTINGS WITH FILES ATTACHED!
            objects = await async_db.scalars(select(Suspension))
            objects_in_db = objects.all()
            object_in_db = [_ for _ in objects_in_db if _.id == suspension_id]
            # patched files:
            file_objects = await async_db.scalars(select(FileAttached))  # == [] when no files attached
            files_in_db = file_objects.all() if file_objects is not None else []
            file_paths = [
                FILES_DIR.joinpath(file_name) for file_name in file_names_added if file_names_added is not None
            ]
            files_to_delete_at_the_end += file_paths
            login_user_response = await ac.post(LOGIN, data=login)
            response = await ac.delete(
                test_url + f"{suspension_id}",
                params=create_params,
                headers={"Authorization": f"Bearer {login_user_response.json()['access_token']}"},
            )
            assert response.status_code == status, f"User: {login} can't get {test_url}. Response: {response.__dict__}"
            if response.status_code != 200:
                await log.ainfo(
                    f"SCENARIO: ___ status_code != 200___ _{scenario_number}_ info: {name}",
                    files_in_db=files_in_db,
                    login_data=login,
                    params=create_params,
                    response=response.json(),
                    status=response.status_code,
                    wings_of_end=f"STATUS: {response.status_code}___ END of SCENARIO: ___ {scenario_number}  _{name}_"
                )
                await delete_files_in_folder(
                    [FILES_DIR.joinpath(file_name) for file_name in file_names_added if file_names_added is not None]
                )
                await clean_test_database(async_db, FileAttached, SuspensionsFiles)  # clean data after failed scenario
                continue
            # run asserts in a scenario:
            # grab objects in db info after testing:
            objects_after = await async_db.scalars(select(Suspension))
            objects_in_db_after = objects_after.all()
            object_in_db_after = [_ for _ in objects_in_db_after if _.id == suspension_id]
            file_objects_after = await async_db.scalars(select(FileAttached))  # == [] when no files attached
            files_in_db_after = file_objects_after.all() if file_objects_after is not None else []
            file_in_db_after = [_ for _ in files_in_db_after if _.id == files_list_set_to_suspension[0]]
            suspension_files_object_after = await async_db.scalars(select(SuspensionsFiles))
            suspension_files_in_db_after = suspension_files_object_after.all()
            all_files_in_folder = [file.name for file in FILES_DIR.glob('*')]
            if file_names_added is not None:
                for file in file_names_added:
                    assert file not in all_files_in_folder, f"{file} in files folder: {FILES_DIR}, but shouldn't"
            expected = {
                "suspensions_after": len(objects_in_db) - 1,
                "suspension_id_in_db": [],
                "file_in_db": [],
            }
            match_values = (
                # name_value, expected_value, exist_value
                ("Suspension id: ", suspension_id, object_in_db[0].id),
                ("Total suspensions after: ", expected.get("suspensions_after"), len(objects_in_db_after)),
                ("No object in db: ", expected.get("suspension_id_in_db"), object_in_db_after),
                ("No file attached in db: ", expected.get("file_in_db"), file_in_db_after),
                ("No file relations in db: ", suspension_files_in_db_before, suspension_files_in_db_after),
            )
            for name_value, expected_value, exist_value in match_values:
                assert expected_value == exist_value, f"{name_value} {exist_value} not as expected: {expected_value}"
            await log.ainfo(
                f"SCENARIO: _{scenario_number}_ info: {name}",
                files_in_db=files_in_db,
                file_names_added=file_names_added,
                files_in_db_after=files_in_db_after,
                objects_in_db=objects_in_db,
                objects_in_db_after=objects_in_db_after,
                login_data=login,
                params=create_params,
                response=response.json(),
                suspension_files_in_db_after=suspension_files_in_db_after,
                suspension_files_in_db_before=suspension_files_in_db_before,
                wings_of_end=f"_______________________________________________ END of SCENARIO: ___ {scenario_number}"
            )
    await clean_test_database(async_db, User, Suspension, FileAttached, SuspensionsFiles)
    await delete_files_in_folder(files_to_delete_at_the_end)
