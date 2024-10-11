"""
Асинхронные тесты работы эндпоинтов задач: tests/test_routes/test_task.py
pytest -s -W ignore::DeprecationWarning
pytest -k test_unauthorized_get_urls -vs
pytest -k test_task.py -vs  # тесты только из этого файла
pytest -vs  # все тесты
https://anyio.readthedocs.io/en/stable/testing.html

pytest -k test_unauthorized_tries_task_urls -vs
pytest -k test_user_get_task_url -vs todo !
pytest -k test_user_get_all_tasks_url -vs
pytest -k test_user_get_all_tasks_opened_url -vs  Todo /api/tasks/opened
pytest -k test_user_get_my_tasks_ordered_url -vs  Todo /api/tasks/my_tasks_ordered
pytest -k test_user_get_my_tasks_todo_url -vs Todo /api/tasks/my_tasks_todo
pytest -k test_user_post_task_form_url -vs  todo !
pytest -k test_user_post_task_with_files_form_url -vs  todo !
pytest -k test_user_patch_task_url -vs todo !
pytest -k test_super_user_delete_task_url -vs todo !

pytest -k test_super_user_add_files_to_task_url -vs todo !

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
from src.core.db.models import FileAttached, Task, TasksFiles, User
from src.settings import settings
from tests.conftest import (clean_test_database, create_test_files,
                            delete_files_in_folder,
                            get_file_names_for_model_db)

log = structlog.get_logger() if settings.FILE_NAME_IN_LOG is False else structlog.get_logger().bind(file_name=__file__)
pytestmark = pytest.mark.anyio  # make all test mark with `anyio` or use decorator: # @pytest.mark.anyio

TASKS_PATH = settings.ROOT_PATH + "/tasks"  # /api/tasks/
FILES_PATH = settings.ROOT_PATH + "/files"  # /api/files/

SERVICES_DIR = Path(__file__).resolve().parent.parent.parent
FILES_DIR = SERVICES_DIR.joinpath(settings.FILES_DOWNLOAD_DIR)
TEST_ROUTES_DIR = Path(__file__).resolve().parent


async def test_unauthorized_tries_task_urls(async_client: AsyncClient) -> None:
    """
    Тестирует доступ к эндпоинтам задач неавторизованным пользователем:
    pytest -k test_unauthorized_tries_task_urls -vs
    """
    get_params_urls = (
        (TASKS_PATH + TASK_ID, {}, 401),  # /api/tasks/{task_id}
        (TASKS_PATH + MAIN_ROUTE, {}, 401),  # /api/tasks/
        (TASKS_PATH + GET_OPENED_ROUTE, {}, 401),  # /api/tasks/opened
        (TASKS_PATH + MY_TASKS, {}, 401),  # /api/tasks/my_tasks_ordered
        (TASKS_PATH + ME_TODO, {}, 401),  # /api/tasks/my_tasks_todo
    )
    patch_data_urls = (
        (TASKS_PATH + TASK_ID, {}, 401),  # /api/tasks/{task_id}
    )
    post_data_urls = (
        (TASKS_PATH + POST_TASK_FORM, {}, 401),  # /api/tasks/post_task_form
        (TASKS_PATH + POST_TASK_FILES_FORM, {}, 401),  # /api/tasks/post_task_with_files_form
        (TASKS_PATH + ADD_FILES_TO_TASK, {}, 401),  # /api/tasks/add_files_to_task
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


# async def test_user_patch_task_url(
#         async_client: AsyncClient,
#         async_db: AsyncSession,
#         tasks_orm: Task,  # todo
#         super_user_orm: User
# ) -> None:
#     """
#     Тестирует редактирование задачи из формы с возможностью дозагрузки файла:
#     pytest -k test_user_patch_task_url -vs
#
#     before_patched - параметры задачи при ее создании: тождественны "scenarios" из tasks_orm в confest.py
#
#     scenarios - тестовые сценарии редактирования задачи (сценарии не изолированы друг от друга).
#     Параметры задачи не сбрасываются на базовые ("scenarios" из tasks_orm в confest.py) в цикле сценариев,
#     поэтому используем разные сценарии при тестировании редактирования параметров задачи.
#
#     expected - словарь ожидаемых значений параметров задачи:
#     если в эндпоинте параметр меняется, то изменяется значение и в словаре, либо берется из БД (при создании задачи).
#
#     match_values - кортеж параметров, используемых в assert (ожидание - реальность).
#
#     """
#     test_url = TASKS_PATH + "/"  # /api/tasks/{task_id}
#     user_orm_login = {"username": "user_fixture@f.com", "password": "testings"}
#     user_settings_email = json.loads(settings.STAFF)["1"]
#     user_settings_login = {"username": user_settings_email, "password": "testings"}
#     super_user_login = {"username": super_user_orm.email, "password": "testings"}
#     now = datetime.now(TZINFO).strftime(DATE_FORMAT)
#     day_ago = (datetime.now(TZINFO) - timedelta(days=1)).strftime(DATE_FORMAT)
#     error_in_date = "11-07-20244"
#     # error_in_time = "11-07-2024: 45:18"
#     test_files = ["testfile.txt", "testfile2.txt", "testfile3.txt"]
#     await create_test_files(test_files)
#     # risk_accident_before_patched = [item for item in json.loads(settings.RISK_SOURCE).values()][0]  # next(iter())
#     tech_process_before_patched = [item for item in json.loads(settings.TECH_PROCESS).values()][0]  # next(iter())
#     before_patched = (
#         (
#             "_1_[]",  # description - [0],
#             datetime.now() - timedelta(days=2),  # suspension_start - [1],
#             datetime.now() - timedelta(days=1, hours=23, minutes=59),  # suspension_finish - [2],
#             "1",  # measures - [3],
#             1,  # user_id - [4],
#         ),
#         ("_[2875_]", datetime.now() - timedelta(days=2), datetime.now() - timedelta(minutes=5), "2", 2),
#         ("[_10_]", datetime.now() - timedelta(minutes=15), datetime.now() - timedelta(minutes=5), "3", 1),
#         ("[_60]_", datetime.now() - timedelta(minutes=30), datetime.now() + timedelta(minutes=30), "4", 2)
#     )
#     scenario_number = 0
#     # Each other dependant scenarios
#     scenarios = (
#         # login, params, status, uploaded_file, suspension_id, name
#         (user_settings_login, {
#             ANALYTICS_START: error_in_time,
#             ANALYTICS_FINISH: day_ago,
#             SUSPENSION_DESCRIPTION: "error_in_time",
#         }, 422, None, 1, "error_in_time"),  # 1
#         (user_settings_login, {
#             ANALYTICS_START: error_in_date,
#             ANALYTICS_FINISH: day_ago,
#             SUSPENSION_DESCRIPTION: "error_in_date",
#         }, 422, None, 1, "error_in_date"),  # 2
#         (user_settings_login, {
#             ANALYTICS_START: now,
#             ANALYTICS_FINISH: day_ago,
#             SUSPENSION_DESCRIPTION: "L > R",
#         }, 422, None, 1, "L > R"),  # 3
#         (
#             user_settings_login, {SUSPENSION_DESCRIPTION: "not author or admin"}, 403, None, 2, "not author or admin"
#         ),  # 4
#         (
#             super_user_login, {SUSPENSION_DESCRIPTION: "admin", IMPLEMENTING_MEASURES: "admin"}, 200, None, 4, "admin"
#         ),  # 5
#         (user_settings_login, {
#             IMPLEMENTING_MEASURES: "Just a single parameter has changed",
#             FILES_UNLINK: False
#         }, 200, None, 1, "Just a single parameter has changed"),  # 6
#         (user_settings_login, {
#             IMPLEMENTING_MEASURES: "Cause the measures have been changed in scenario 4 need to edit again",
#             FILES_UNLINK: True
#         }, 200, [], 1, "FILES_UNLINK TRUE when there is no files"),  # 7
#         (user_orm_login, {}, 200, None, 2, "empty params / suspension_id = 2 -> user_orm_login"),  # 8
#         (user_settings_login, {
#             ANALYTICS_START: day_ago,
#             ANALYTICS_FINISH: now,
#             SUSPENSION_DESCRIPTION: "test_description_patched",
#             IMPLEMENTING_MEASURES: "test_measures",
#             TECH_PROCESS: json.loads(settings.TECH_PROCESS)["SPEC_DEP_26"],
#             RISK_ACCIDENT_SOURCE: json.loads(settings.RISK_SOURCE)["ANOTHER"],
#             FILES_UNLINK: False
#         }, 200, None, 1, "with params / suspension_id = 1"),  # 9
#         (user_orm_login, {}, 200, {"file_to_upload": open(TEST_ROUTES_DIR.joinpath(test_files[0]), "rb")}, 2,
#          "empty params with 1 file, suspension_id = 2"),  # 10
#         (user_orm_login, {}, 200, {"file_to_upload": open(TEST_ROUTES_DIR.joinpath(test_files[1]), "rb")}, 2,
#          "add 1 more file (total 2 files), suspension_id = 2"),  # 11
#         (user_orm_login, {}, 200, {"file_to_upload": open(TEST_ROUTES_DIR.joinpath(test_files[2]), "rb")}, 2,
#          "add 1 more file (total 3 files), suspension_id = 2"),  # 12
#         (user_orm_login,
#             {FILES_UNLINK: True}, 406, {"file_to_upload": open(TEST_ROUTES_DIR.joinpath(test_files[2]), "rb")}, 2,
#          "unlink files simultaneously with upload"),  # 13
#         (user_orm_login, {FILES_UNLINK: True}, 200, None, 2, "and now unlink all the files"),  # 14
#     )
#     async with async_client as ac:
#         for login, create_params, status, uploaded_file, suspension_id, name in scenarios:
#             scenario_number += 1
#             await log.ainfo(f"*************  SCENARIO: ___ {scenario_number} ___  ***** {name}  ***************")
#             # gather info of objects in db before testing:
#             objects_before = await async_db.scalars(select(Suspension))  # сколько объектов до сценария
#             objects_in_db_before = objects_before.all()  # сколько объектов до сценария
#             object_before_to_patch = [
#                 suspension for suspension in objects_in_db_before if suspension.id == suspension_id
#             ]
#             suspension_files_object_before = await async_db.scalars(select(SuspensionsFiles))
#             suspension_files_in_db_before = suspension_files_object_before.all()
#             attached_files_objects_before = await async_db.scalars(  # какие файлы были привязаны к простою
#                 select(FileAttached)
#                 .join(Suspension.files)
#                 .where(Suspension.id == suspension_id)
#             )
#             attached_files_in_db_before = attached_files_objects_before.all()
#             attached_files_paths_before = [
#                 FILES_DIR.joinpath(file.name) for file in attached_files_in_db_before
#                 if attached_files_in_db_before is not None
#             ]
#             if suspension_files_in_db_before:
#                 suspension_files_records_before = [
#                     (record.suspension_id, record.file_id) for record in suspension_files_in_db_before
#                 ]
#             else:
#                 suspension_files_records_before = []
#             response_login_user = await ac.post(LOGIN, data=login)
#             response = await ac.patch(
#                 test_url + f"{suspension_id}",
#                 params=create_params,
#                 headers={"Authorization": f"Bearer {response_login_user.json()['access_token']}"},
#                 files=uploaded_file
#             )
#             assert response.status_code == status, (
#                 f"User: {login} couldn't get {test_url}. Response: {response.__dict__}"
#             )
#             if response.status_code != 200:
#                 await log.ainfo(
#                     f"SCENARIO: _{scenario_number}_ info: {name}",
#                     login_data=login,
#                     orm_before_patched={
#                         "orm_description": before_patched[suspension_id - 1][0],
#                         "orm_start": before_patched[suspension_id - 1][1].strftime(DATE_TIME_FORMAT),
#                         "orm_finish": before_patched[suspension_id - 1][2].strftime(DATE_TIME_FORMAT),
#                         "duration": before_patched[suspension_id - 1][2] - before_patched[suspension_id - 1][1],
#                     },
#                     params=create_params,
#                     response=response.json(),
#                     status=response.status_code,
#                     wings_of_end=f"STATUS: {response.status_code}___ END of SCENARIO: ___ {scenario_number}  _{name}_"
#                 )
#                 continue
#             # current_user: author or super_user?
#             current_user = await async_db.scalar(select(User).where(User.email == login.get("username")))
#             # patched suspensions:
#             objects = await async_db.scalars(select(Suspension))
#             objects_in_db = objects.all()
#             object_in_db = [obj for obj in objects_in_db if obj.id == suspension_id][0]
#             # patched files:
#             files_in_response = response.json().get(FILES_SET_TO)
#             file_objects = await async_db.scalars(select(FileAttached))  # == [] when no files attached
#             files_in_db = file_objects.all() if file_objects is not None else []
#             file_paths = [
#                 FILES_DIR.joinpath(file_name) for file_name in files_in_response if files_in_response is not None
#             ]
#             all_files_in_folder = [file.name for file in FILES_DIR.glob('*')]
#             # patched files relations:
#             suspension_files_object = await async_db.scalars(select(SuspensionsFiles))
#             suspension_files_in_db = suspension_files_object.all()
#             suspension_files_records = set(
#                 ((record.suspension_id, record.file_id) for record in suspension_files_in_db)
#             )
#             if uploaded_file and (create_params.get(FILES_UNLINK) is not True):
#                 suspension_files_in_scenario = (
#                     tuple(suspension_files_records_before)
#                     + ((suspension_id, len(suspension_files_records_before) + 1),)
#                 )
#             elif create_params.get(FILES_UNLINK):
#                 suspension_files_in_scenario = ()
#             else:
#                 suspension_files_in_scenario = tuple(suspension_files_records_before)
#             # expected values in scenario
#             expected = {
#                 "total_suspensions_expected": len(objects_in_db_before),
#                 "files_attached": await get_file_names_for_model_db(async_db, Suspension, object_in_db.id),
#                 "suspension_files": suspension_files_in_scenario,
#                 "start": (
#                     create_params.get(ANALYTICS_START) if create_params.get(ANALYTICS_START) is not None
#                     else before_patched[suspension_id - 1][1].strftime(DATE_TIME_FORMAT)
#                 ),
#                 "finish": (
#                     create_params.get(ANALYTICS_FINISH) if create_params.get(ANALYTICS_FINISH) is not None
#                     else before_patched[suspension_id - 1][2].strftime(DATE_TIME_FORMAT)
#                 ),
#                 "description": (
#                     create_params.get(SUSPENSION_DESCRIPTION) if create_params.get(SUSPENSION_DESCRIPTION) is not None
#                     else before_patched[suspension_id - 1][0]
#                 ),
#                 "measures": (
#                     create_params.get(IMPLEMENTING_MEASURES) if create_params.get(IMPLEMENTING_MEASURES) is not None
#                     else before_patched[suspension_id - 1][3]
#                 ),
#                 "risk_accident": (
#                     create_params.get(RISK_ACCIDENT_SOURCE) if create_params.get(RISK_ACCIDENT_SOURCE) is not None
#                     else risk_accident_before_patched
#                 ),
#                 "tech_process": (
#                     create_params.get(TECH_PROCESS) if create_params.get(TECH_PROCESS) is not None
#                     else tech_process_before_patched
#                 ),
#                 "user_id": (object_before_to_patch[0].user_id if current_user.is_superuser is not True
#                             else current_user.id)
#             }
#             # run asserts in a scenario:
#             match_values = (
#                 # name_value, expected_value, exist_value
#                 ("Suspension id: ", suspension_id, object_in_db.id),
#                 ("Total suspensions: ", expected.get("total_suspensions_expected"), len(objects_in_db)),
#                 ("Attached files: ", set(expected.get("files_attached")), set(files_in_response)),
#                 ("Suspension files: ", set(expected.get("suspension_files")), suspension_files_records),
#                 (
#                     "Suspension start: ",
#                     expected.get("start"),
#                     object_in_db.suspension_start.strftime(DATE_TIME_FORMAT)
#                 ),
#                 (
#                     "Suspension finish: ",
#                     expected.get("finish"),
#                     object_in_db.suspension_finish.strftime(DATE_TIME_FORMAT)
#                 ),
#                 ("Description: ", expected.get("description"), object_in_db.description),
#                 ("Implementing measures: ", expected.get("measures"), object_in_db.implementing_measures),
#                 ("Risk accident: ", expected.get("risk_accident"), object_in_db.risk_accident),
#                 ("Tech_process: ", int(expected.get("tech_process")), object_in_db.tech_process),
#                 (
#                     "Duration: ",
#                     (
#                         datetime.strptime(expected["finish"], DATE_TIME_FORMAT)
#                         - datetime.strptime(expected["start"], DATE_TIME_FORMAT)
#                     ),
#                     object_in_db.suspension_finish - object_in_db.suspension_start
#                 ),
#                 ("user_id: ", expected.get("user_id"), object_in_db.user_id),
#                 # (": ",),  # more scenarios
#             )
#             for name_value, expected_value, exist_value in match_values:
#                 assert expected_value == exist_value, f"{name_value} {exist_value} not as expected: {expected_value}"
#             if files_in_response is not None:
#                 for file in files_in_response:
#                     assert file in all_files_in_folder, f"Can't find: {file} in files folder: {FILES_DIR}"
#             if create_params.get(FILES_UNLINK) is True and attached_files_paths_before:
#                 for file in attached_files_paths_before:
#                     assert file.name not in all_files_in_folder, f"File: {file} is not deleted in folder: {FILES_DIR}"
#             await log.ainfo(
#                 f"SCENARIO: _{scenario_number}_ info: {name}",
#                 files_attached_before=attached_files_paths_before,
#                 files_attached_expected=expected.get("files_attached"),
#                 files_in_db=files_in_db,
#                 files_in_response=files_in_response,
#                 file_paths=file_paths,
#                 login_data=login,
#                 orm_before_patched={
#                     "orm_description": before_patched[suspension_id - 1][0],
#                     "orm_start": before_patched[suspension_id - 1][1].strftime(DATE_TIME_FORMAT),
#                     "orm_finish": before_patched[suspension_id - 1][2].strftime(DATE_TIME_FORMAT),
#                     "duration": before_patched[suspension_id - 1][2] - before_patched[suspension_id - 1][1],
#                 },
#                 params=create_params,
#                 response=response.json(),
#                 suspension_files_expected=set(expected.get("suspension_files")),
#                 wings_of_end=f"_______________________________________________ END of SCENARIO: ___ {scenario_number}"
#             )
#     await clean_test_database(async_db, User, Suspension, FileAttached, SuspensionsFiles)  # а файлы удаляются в апи


# async def test_user_post_suspension_with_files_form_url(
#         async_client: AsyncClient,
#         async_db: AsyncSession,
#         user_orm: User,
# ) -> None:
#     """
#     Тестирует фиксацию случая простоя из формы с обязательной загрузкой нескольких файлов:
#     pytest -k test_user_post_suspension_with_files_form_url -vs
#
#     scenarios - тестовые сценарии создания простоев (сценарии изолированы).
#     expected - словарь ожидаемых значений параметров простоя
#     match_values - кортеж параметров, используемых в assert (ожидание - реальность).
#     """
#     test_url = SUSPENSIONS_PATH + POST_SUSPENSION_FILES_FORM  # /api/suspensions/post_suspension_with_files_form
#     user_orm_login = {"username": "user_fixture@f.com", "password": "testings"}
#     now = datetime.now(TZINFO).strftime(DATE_TIME_FORMAT)
#     day_ago = (datetime.now(TZINFO) - timedelta(days=1)).strftime(DATE_TIME_FORMAT)
#     error_in_date = "11-07-20244: 18:45"
#     error_in_time = "11-07-2024: 45:18"
#     test_files = ["testfile.txt", "testfile2.txt", "testfile3.txt"]
#     await create_test_files(test_files)
#     files = [
#         ("files_to_upload", open(TEST_ROUTES_DIR.joinpath(test_files[0]), "rb")),
#         ("files_to_upload", open(TEST_ROUTES_DIR.joinpath(test_files[1]), "rb")),
#         ("files_to_upload", open(TEST_ROUTES_DIR.joinpath(test_files[2]), "rb"))
#     ]
#     scenario_number = 0
#     scenarios = (
#         # login, params, status, files, name
#         (user_orm_login, {
#             ANALYTICS_START: error_in_time,
#             ANALYTICS_FINISH: day_ago,
#             SUSPENSION_DESCRIPTION: "error_in_time",
#             IMPLEMENTING_MEASURES: "test_measures",
#             TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
#             RISK_ACCIDENT_SOURCE: json.loads(settings.RISK_SOURCE)["ANOTHER"]
#         }, 422, files, "error_in_time"),  # 1
#         (user_orm_login, {
#             ANALYTICS_START: now,
#             ANALYTICS_FINISH: error_in_date,
#             SUSPENSION_DESCRIPTION: "error_in_date",
#             IMPLEMENTING_MEASURES: "test_measures",
#             TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
#             RISK_ACCIDENT_SOURCE: json.loads(settings.RISK_SOURCE)["ANOTHER"]
#         }, 422, files, "error_in_date"),  # 2
#         (user_orm_login, {
#             ANALYTICS_START: now,
#             ANALYTICS_FINISH: day_ago,
#             SUSPENSION_DESCRIPTION: "L > R",
#             IMPLEMENTING_MEASURES: "test_measures",
#             TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
#             RISK_ACCIDENT_SOURCE: json.loads(settings.RISK_SOURCE)["ANOTHER"]
#         }, 422, files, "L > R"),  # 3
#         (user_orm_login, {
#             ANALYTICS_START: day_ago,
#             ANALYTICS_FINISH: now,
#             SUSPENSION_DESCRIPTION: "no files to upload - None",
#             IMPLEMENTING_MEASURES: "test_measures",
#             TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
#             RISK_ACCIDENT_SOURCE: json.loads(settings.RISK_SOURCE)["ANOTHER"]
#         }, 422, None, "no files to upload"),  # 4
#         (user_orm_login, {
#             ANALYTICS_START: day_ago,
#             ANALYTICS_FINISH: now,
#             SUSPENSION_DESCRIPTION: "no files to upload - []",
#             IMPLEMENTING_MEASURES: "test_measures",
#             TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
#             RISK_ACCIDENT_SOURCE: json.loads(settings.RISK_SOURCE)["ANOTHER"]
#         }, 422, [], "no files to upload"),  # 5
#         (user_orm_login, {
#             ANALYTICS_START: day_ago,
#             ANALYTICS_FINISH: now,
#             SUSPENSION_DESCRIPTION: "with files",
#             IMPLEMENTING_MEASURES: "test_measures",
#             TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
#             RISK_ACCIDENT_SOURCE: json.loads(settings.RISK_SOURCE)["ANOTHER"]
#         }, 200, files, "with files"),  # 6
#     )
#     async with async_client as ac:
#         for login, create_params, status, files, name in scenarios:
#             scenario_number += 1
#             await log.awarning(f"*************  SCENARIO: ___ {scenario_number} ___  *****  {name}   ******")
#             response_login_user = await ac.post(LOGIN, data=login)
#             response = await ac.post(
#                 test_url,
#                 params=create_params,
#                 headers={"Authorization": f"Bearer {response_login_user.json()['access_token']}"},
#                 files=files
#             )
#             assert response.status_code == status, (
#                 f"User: {login} couldn't get {test_url}. Response: {response.__dict__}"
#             )
#             if response.status_code != 200:
#                 await log.ainfo(
#                     f"SCENARIO: _{scenario_number}_ info: ",
#                     login_data=login,
#                     params=create_params,
#                     response=response.json(),
#                     status=response.status_code,
#                     wings_of_end=f"STATUS: {response.status_code}___ END of SCENARIO: ___ {scenario_number} ___ {name}"
#                 )
#                 continue
#             # created suspensions:
#             objects = await async_db.scalars(select(Suspension))
#             objects_in_db = objects.all()
#             new_object = objects_in_db[0] if objects_in_db is not None else None
#             # created files relations:
#             suspension_files_object = await async_db.scalars(select(SuspensionsFiles))
#             suspension_files_in_db = suspension_files_object.all()
#             suspension_files_records = set(
#                 ((record.suspension_id, record.file_id) for record in suspension_files_in_db)
#             )
#             total_suspensions = len(objects_in_db) if objects_in_db is not None else None
#             # files attached:
#             file_objects = await async_db.scalars(select(FileAttached))
#             files_in_db = file_objects.all()
#             files_in_response = response.json().get(FILES_SET_TO)
#             all_files_in_folder = [file.name for file in FILES_DIR.glob('*')]
#             file_paths = [
#                 FILES_DIR.joinpath(file_name) for file_name in files_in_response if files_in_response is not None
#             ]
#             # expected values in scenario
#             expected = {
#                 "total_suspensions_expected": 1,
#                 "suspensions_expected_id": response.json()["id"],
#                 "files_attached": await get_file_names_for_model_db(async_db, Suspension, new_object.id),
#                 "suspension_files": set(((response.json()["id"], index[0] + 1) for index in enumerate(test_files))),
#                 "start": create_params.get(ANALYTICS_START),
#                 "finish": create_params.get(ANALYTICS_FINISH),
#                 "description": create_params.get(SUSPENSION_DESCRIPTION),
#                 "measures": create_params.get(IMPLEMENTING_MEASURES),
#                 "risk_accident": create_params.get(RISK_ACCIDENT_SOURCE),
#                 "tech_process": create_params.get(TECH_PROCESS),
#                 "user_id": user_orm.id,
#             }
#             # run asserts in a scenario:
#             match_values = (
#                 # name_value, expected_value, exist_value
#                 ("Suspension id: ", expected.get("suspensions_expected_id"), new_object.id),
#                 ("Total suspensions: ", expected.get("total_suspensions_expected"), total_suspensions),
#                 ("Attached files: ", set(expected.get("files_attached")), set(files_in_response)),
#                 ("Suspension files: ", set(expected.get("suspension_files")), suspension_files_records),
#                 ("Suspension start: ", expected.get("start"), new_object.suspension_start.strftime(DATE_TIME_FORMAT)),
#                 (
#                     "Suspension finish: ",
#                     expected.get("finish"),
#                     new_object.suspension_finish.strftime(DATE_TIME_FORMAT)
#                 ),
#                 ("Description: ", expected.get("description"), new_object.description),
#                 ("Implementing measures: ", expected.get("measures"), new_object.implementing_measures),
#                 ("Risk accident: ", expected.get("risk_accident"), new_object.risk_accident),
#                 ("Tech_process: ", int(expected.get("tech_process")), new_object.tech_process),
#                 (
#                     "Duration: ",
#                     (
#                         datetime.strptime(expected["finish"], DATE_TIME_FORMAT)
#                         - datetime.strptime(expected["start"], DATE_TIME_FORMAT)
#                     ),
#                     new_object.suspension_finish - new_object.suspension_start
#                 ),
#                 ("user_id: ", expected.get("user_id"), new_object.user_id),
#                 # (": ",),  # more scenarios
#             )
#             for name_value, expected_value, exist_value in match_values:
#                 assert expected_value == exist_value, f"{name_value} {exist_value} not as expected: {expected_value}"
#             if files_in_response is not None:
#                 for file in files_in_response:
#                     assert file in all_files_in_folder, f"Can't find: {file} in files folder: {FILES_DIR}"
#             await log.awarning(
#                 f"SCENARIO: _{scenario_number}_ info: {name} ",
#                 files_attached_expected=expected.get("files_attached"),
#                 files_in_db=files_in_db,
#                 files_in_response=files_in_response,
#                 file_paths=file_paths,
#                 login_data=login,
#                 params=create_params,
#                 response=response.json(),
#                 suspension_files_records=suspension_files_records,
#                 suspension_files_expected=expected.get("suspension_files"),
#                 wings_of_end=f"_________________________ END of SCENARIO: ___ {scenario_number} ___ {name} ___"
#             )
#             await clean_test_database(async_db, User, Suspension, FileAttached, SuspensionsFiles)
#             await delete_files_in_folder(file_paths)
#
#
# async def test_user_post_suspension_form_url(
#         async_client: AsyncClient,
#         async_db: AsyncSession,
#         user_orm: User,
# ) -> None:
#     """
#     Тестирует фиксацию случая простоя из формы с возможностью загрузки 1 файла:
#     pytest -k test_user_post_suspension_form_url -vs
#
#     scenarios - тестовые сценарии создания простоев (все сценарии изолированы).
#     expected - словарь ожидаемых значений параметров простоя
#     match_values - кортеж параметров, используемых в assert (ожидание - реальность).
#     """
#     test_url = SUSPENSIONS_PATH + POST_SUSPENSION_FORM  # /api/suspensions/post_suspension_form
#     user_orm_login = {"username": "user_fixture@f.com", "password": "testings"}
#     now = datetime.now(TZINFO).strftime(DATE_TIME_FORMAT)
#     day_ago = (datetime.now(TZINFO) - timedelta(days=1)).strftime(DATE_TIME_FORMAT)
#     error_in_date = "11-07-20244: 18:45"
#     error_in_time = "11-07-2024: 45:18"
#     test_files = ["testfile.txt"]
#     await create_test_files(test_files)
#     file_to_upload = {"file_to_upload": open(TEST_ROUTES_DIR.joinpath(test_files[0]), "rb")}
#     scenario_number = 0
#     scenarios = (
#         # login, params, status, file_to_upload, name
#         (user_orm_login, {
#             ANALYTICS_START: error_in_time,
#             ANALYTICS_FINISH: day_ago,
#             SUSPENSION_DESCRIPTION: "error_in_time",
#             IMPLEMENTING_MEASURES: "test_measures",
#             TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
#             RISK_ACCIDENT_SOURCE: json.loads(settings.RISK_SOURCE)["ANOTHER"]
#         }, 422, None, "error_in_time"),  # 1
#         (user_orm_login, {
#             ANALYTICS_START: now,
#             ANALYTICS_FINISH: error_in_date,
#             SUSPENSION_DESCRIPTION: "error_in_date",
#             IMPLEMENTING_MEASURES: "test_measures",
#             TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
#             RISK_ACCIDENT_SOURCE: json.loads(settings.RISK_SOURCE)["ANOTHER"]
#         }, 422, None, "error_in_date"),  # 2
#         (user_orm_login, {
#             ANALYTICS_START: now,
#             ANALYTICS_FINISH: day_ago,
#             SUSPENSION_DESCRIPTION: "L > R",
#             IMPLEMENTING_MEASURES: "test_measures",
#             TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
#             RISK_ACCIDENT_SOURCE: json.loads(settings.RISK_SOURCE)["ANOTHER"]
#         }, 422, None, "3 L > R"),  # 3
#         (user_orm_login, {
#             ANALYTICS_START: day_ago,
#             ANALYTICS_FINISH: now,
#             SUSPENSION_DESCRIPTION: "no files to upload - None",
#             IMPLEMENTING_MEASURES: "test_measures",
#             TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
#             RISK_ACCIDENT_SOURCE: json.loads(settings.RISK_SOURCE)["ANOTHER"]
#         }, 200, None, "no files to upload"),  # 4
#         (user_orm_login, {
#             ANALYTICS_START: day_ago,
#             ANALYTICS_FINISH: now,
#             SUSPENSION_DESCRIPTION: "with files",
#             IMPLEMENTING_MEASURES: "test_measures",
#             TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
#             RISK_ACCIDENT_SOURCE: json.loads(settings.RISK_SOURCE)["ANOTHER"]
#         }, 200, file_to_upload, "with files"),  # 5
#     )
#     async with async_client as ac:
#         for login, create_params, status, files, name in scenarios:
#             scenario_number += 1
#             await log.awarning(f"*************  SCENARIO: ___ {scenario_number} ___  {name} ___*****************")
#             response_login_user = await ac.post(LOGIN, data=login)
#             response = await ac.post(
#                 test_url,
#                 params=create_params,
#                 headers={"Authorization": f"Bearer {response_login_user.json()['access_token']}"},
#                 files=files
#             )
#             assert response.status_code == status, (
#                 f"User: {login} couldn't get {test_url}. Response: {response.__dict__}"
#             )
#             if response.status_code != 200:
#                 await log.ainfo(
#                     f"SCENARIO: _{scenario_number}___ {name}___ info: ",
#                     login_data=login,
#                     params=create_params,
#                     response=response.json(),
#                     status=response.status_code,
#                     wings_of_end=f"STATUS: {response.status_code}___ END of SCENARIO: ___ {scenario_number}___ {name}"
#                 )
#                 continue
#             # created suspensions:
#             objects = await async_db.scalars(select(Suspension))
#             objects_in_db = objects.all()
#             new_object = objects_in_db[0] if objects_in_db is not None else None
#             total_suspensions = len(objects_in_db) if objects_in_db is not None else None
#             # files attached:
#             file_objects = await async_db.scalars(select(FileAttached))
#             files_in_db = file_objects.all()
#             files_in_response = response.json().get(FILES_SET_TO)
#             all_files_in_folder = [file.name for file in FILES_DIR.glob('*')]
#             file_paths = [
#                 FILES_DIR.joinpath(file_name) for file_name in files_in_response if files_in_response is not None
#             ]
#             # created files relations:
#             suspension_files_object = await async_db.scalars(select(SuspensionsFiles))
#             suspension_files_in_db = suspension_files_object.all()
#             suspension_files_records = set(
#                 ((record.suspension_id, record.file_id) for record in suspension_files_in_db)
#             )
#             # expected values in scenario
#             expected = {
#                 "total_suspensions_expected": 1,
#                 "suspensions_expected_id": response.json()["id"],
#                 "files_attached": await get_file_names_for_model_db(async_db, Suspension, new_object.id),
#                 "suspension_files": set(
#                     ((response.json()["id"], index[0] + 1) for index in enumerate(files_in_response))
#                 ),
#                 "start": create_params.get(ANALYTICS_START),
#                 "finish": create_params.get(ANALYTICS_FINISH),
#                 "description": create_params.get(SUSPENSION_DESCRIPTION),
#                 "measures": create_params.get(IMPLEMENTING_MEASURES),
#                 "risk_accident": create_params.get(RISK_ACCIDENT_SOURCE),
#                 "tech_process": create_params.get(TECH_PROCESS),
#                 "user_id": user_orm.id,
#             }
#             # run asserts in a scenario:
#             match_values = (
#                 # name_value, expected_value, exist_value
#                 ("Suspension id: ", expected.get("suspensions_expected_id"), new_object.id),
#                 ("Total suspensions: ", expected.get("total_suspensions_expected"), total_suspensions),
#                 ("Attached files: ", set(expected.get("files_attached")), set(files_in_response)),
#                 ("Suspension files: ", set(expected.get("suspension_files")), suspension_files_records),
#                 ("Suspension start: ", expected.get("start"), new_object.suspension_start.strftime(DATE_TIME_FORMAT)),
#                 (
#                     "Suspension finish: ",
#                     expected.get("finish"),
#                     new_object.suspension_finish.strftime(DATE_TIME_FORMAT)
#                 ),
#                 ("Description: ", expected.get("description"), new_object.description),
#                 ("Implementing measures: ", expected.get("measures"), new_object.implementing_measures),
#                 ("Risk accident: ", expected.get("risk_accident"), new_object.risk_accident),
#                 ("Tech_process: ", int(expected.get("tech_process")), new_object.tech_process),
#                 (
#                     "Duration: ",
#                     (
#                         datetime.strptime(expected["finish"], DATE_TIME_FORMAT)
#                         - datetime.strptime(expected["start"], DATE_TIME_FORMAT)
#                     ),
#                     new_object.suspension_finish - new_object.suspension_start
#                 ),
#                 ("user_id: ", expected.get("user_id"), new_object.user_id),
#             )
#             for name_value, expected_value, exist_value in match_values:
#                 assert expected_value == exist_value, f"{name_value} {exist_value} not as expected: {expected_value}"
#             if files_in_response is not None:
#                 for file in files_in_response:
#                     assert file in all_files_in_folder, f"Can't find: {file} in files folder: {FILES_DIR}"
#             await log.awarning(
#                 f"SCENARIO: _{scenario_number}_ info: {name}",
#                 files_attached_expected=expected.get("files_attached"),
#                 files_in_db=files_in_db,
#                 files_in_response=files_in_response,
#                 file_paths=file_paths,
#                 login_data=login,
#                 params=create_params,
#                 response=response.json(),
#                 suspension_files_records=suspension_files_records,
#                 suspension_files_expected=expected.get("suspension_files"),
#                 wings_of_end=f"_________ END of SCENARIO: ___ {scenario_number}___ {name}"
#             )
#             await clean_test_database(async_db, Suspension, FileAttached, SuspensionsFiles)
#             await delete_files_in_folder(file_paths)
#     await clean_test_database(async_db, User)
#
#  TODO:
# async def test_user_get_suspension_url(
#         async_client: AsyncClient,
#         async_db: AsyncSession,
#         suspensions_orm: Suspension,
# ) -> None:
#     """
#     Тестирует возможность получения по id информации о случае простоя, или загрузки прикрепленных файлов:
#     pytest -k test_user_get_suspension_url -vs
#
#     before_patched - параметры простоя при его создании: тождественны "scenarios" из suspensions_orm в confest.py
#
#     scenarios - тестовые сценарии редактирования простоев (сценарии не изолированы друг от друга).
#     Параметры простоев не сбрасываются на базовые ("scenarios" из suspensions_orm в confest.py) в цикле сценариев,
#     поэтому используем разные сценарии при тестировании редактирования параметров простая.
#
#     expected - словарь ожидаемых значений параметров простоя:
#     если в эндпоинте параметр меняется, то изменяется значение и в словаре, либо берется из БД (при создании простоя).
#
#     match_values - кортеж параметров, используемых в assert (ожидание - реальность).
#
#     """
#     test_url = SUSPENSIONS_PATH + "/"  # /api/suspensions/{suspension_id}
#     user_orm_login = {"username": "user_fixture@f.com", "password": "testings"}
#     test_files = ["testfile.txt", "testfile2.txt", "testfile3.txt"]
#     await create_test_files(test_files)
#     file_to_attach = {"file_to_upload": open(TEST_ROUTES_DIR.joinpath(test_files[0]), "rb")}  # todo
#     json_choice = [item for item in json.loads(settings.CHOICE_DOWNLOAD_FILES).values()][0]  # next(iter())
#     files_choice = [item for item in json.loads(settings.CHOICE_DOWNLOAD_FILES).values()][1]  # 2nd == "files"
#     scenario_number = 0
#     scenarios = (
#         # login, params, status, uploaded_file, suspension_id, name
#         (user_orm_login, {CHOICE_FORMAT: json_choice}, 200, None, 1, "json-choice"),  # 1
#         (user_orm_login, {CHOICE_FORMAT: json_choice}, 200, None, 2, "json-choice"),  # 2
#         (user_orm_login, {CHOICE_FORMAT: files_choice}, 404, None, 2, "files_choice when no files attached"),  # 3
#         (user_orm_login, {CHOICE_FORMAT: json_choice}, 200, file_to_attach, 2, "patch object by adding a file"),  # 4
#         (user_orm_login, {CHOICE_FORMAT: json_choice}, 200, file_to_attach, 2, "adding one more file to object"),  # 5
#         (user_orm_login, {CHOICE_FORMAT: files_choice}, 200, None, 2, "and now try to get attached files"),  # 6
#     )
#     async with async_client as ac:
#         for login, params, status, uploaded_file, suspension_id, name in scenarios:
#             scenario_number += 1
#             await log.ainfo(f"*************  SCENARIO: ___ {scenario_number} ___  *****  {name}  *************")
#             # gather info of objects in db before testing:
#             objects_before = await async_db.scalars(select(Suspension))  # сколько объектов до сценария
#             objects_in_db_before = objects_before.all()  # сколько объектов до сценария
#             object_before_testing = [obj for obj in objects_in_db_before if obj.id == suspension_id][0]
#             attached_files_objects_before = await async_db.scalars(  # какие файлы были привязаны к простою
#                 select(FileAttached)
#                 .join(Suspension.files)
#                 .where(Suspension.id == suspension_id)
#             )
#             attached_files_in_db_before = attached_files_objects_before.all()
#             attached_files_paths_before = [
#                 FILES_DIR.joinpath(file.name) for file in attached_files_in_db_before
#                 if attached_files_in_db_before is not None
#             ]
#             response_login_user = await ac.post(LOGIN, data=login)
#             if uploaded_file is not None:  # adding file to the object_id in order to get this file later
#                 response_patched = await ac.patch(
#                     test_url + f"{suspension_id}",
#                     params={SUSPENSION_DESCRIPTION: "suspension is attached with files"},
#                     headers={"Authorization": f"Bearer {response_login_user.json()['access_token']}"},
#                     files=uploaded_file
#                 )
#                 assert response_patched.status_code == status, (
#                     f"User: {login} couldn't patch {test_url}. Response: {response.__dict__}"
#                 )
#             response = await ac.get(
#                 test_url + f"{suspension_id}",
#                 params=params,
#                 headers={"Authorization": f"Bearer {response_login_user.json()['access_token']}"},
#             )
#             assert response.status_code == status, (
#                 f"User: {login} couldn't get {test_url}. Response: {response.__dict__}"
#             )
#             if response.status_code != 200:
#                 await log.ainfo(
#                     f"SCENARIO: _{scenario_number}_ info: {name}",
#                     login_data=login,
#                     response=response.json(),
#                     status=response.status_code,
#                     wings_of_end=f"STATUS: {response.status_code}___ END of SCENARIO: ___ {scenario_number}  __{name}"
#                 )
#                 continue
#             if params.get(CHOICE_FORMAT) == files_choice:
#                 # checking only file zip_name correct in headers
#                 zip_name = response.headers.get("content-disposition").split(";")[1].split("=")[1]
#                 expected_zip_name = FILE_NAME_SAVE_FORMAT + "_archive.zip"
#                 assert zip_name == expected_zip_name, (
#                     f"Chosen file_choice: {files_choice}, but couldn't get {expected_zip_name}. "
#                     f"Headers: {response.headers}. Dict: {response.__dict__}"
#                 )
#                 await log.ainfo(
#                     f"SCENARIO: _{scenario_number}_ files_choice: {name}",
#                     login_data=login,
#                     headers=response.headers,
#                     wings_of_end=f"STATUS: {response.status_code}_ END of SCENARIO: _ {scenario_number}____{name}!!"
#                 )
#                 await delete_files_in_folder(file_paths)
#                 continue
#             # suspensions after test running:
#             objects = await async_db.scalars(select(Suspension))
#             objects_in_db = objects.all()
#             object_in_db = [obj for obj in objects_in_db if obj.id == suspension_id][0]
#             # files after test running:
#             files_in_response = response.json().get(FILES_SET_TO)
#             file_objects = await async_db.scalars(select(FileAttached))  # == [] when no files attached
#             files_in_db = file_objects.all() if file_objects is not None else []
#             file_paths = [
#                 FILES_DIR.joinpath(file_name) for file_name in files_in_response if files_in_response is not None
#             ]
#             all_files_in_folder = [file.name for file in FILES_DIR.glob('*')]
#             # files relations after test running:
#             suspension_files_object = await async_db.scalars(select(SuspensionsFiles))
#             suspension_files_in_db = suspension_files_object.all()
#             suspension_files_records = set(
#                 ((record.suspension_id, record.file_id) for record in suspension_files_in_db)
#             )
#             suspension_files_in_scenario = tuple(suspension_files_records)
#             # expected values in scenario
#             expected = {
#                 "total_expected_before": len(objects_in_db_before),
#                 "files_attached": await get_file_names_for_model_db(async_db, Suspension, object_before_testing.id),
#                 "suspension_files": suspension_files_in_scenario,
#                 "start": object_before_testing.suspension_start,
#                 "finish": object_before_testing.suspension_finish,
#                 "description": object_before_testing.description,
#                 "measures": object_before_testing.implementing_measures,
#                 "risk_accident": object_before_testing.risk_accident,
#                 "tech_process": int(object_before_testing.tech_process),
#                 "user_id": object_before_testing.user_id,
#             }
#             # run asserts in a scenario:
#             match_values = (
#                 # name_value, expected_value, exist_value
#                 ("Suspension id: ", suspension_id, object_before_testing.id),
#                 ("Total suspensions: ", expected.get("total_expected_before"), len(objects_in_db)),
#                 ("Attached files after: ", set(expected.get("files_attached")), set(files_in_response)),
#                 ("Suspension files: ", set(expected.get("suspension_files")), suspension_files_records),
#                 ("Suspension start: ", expected.get("start"), object_in_db.suspension_start),
#                 ("Suspension finish: ", expected.get("finish"), object_in_db.suspension_finish),
#                 ("Description: ", expected.get("description"), object_in_db.description),
#                 ("Implementing measures: ", expected.get("measures"), object_in_db.implementing_measures),
#                 ("Risk accident: ", expected.get("risk_accident"), object_in_db.risk_accident),
#                 (
#                     "Tech process: ",
#                     expected.get("tech_process"),
#                     int(json.loads(settings.TECH_PROCESS).get(response.json().get(TECH_PROCESS)))
#                 ),
#                 (
#                     "Duration: ",
#                     (
#                         (object_before_testing.suspension_finish
#                             - object_before_testing.suspension_start).total_seconds() / SUSPENSION_DURATION_RESPONSE
#                     ),
#                     response.json().get(SUSPENSION_DURATION)
#                 ),
#                 ("user_id: ", expected.get("user_id"), object_in_db.user_id),
#             )
#             for name_value, expected_value, exist_value in match_values:
#                 assert expected_value == exist_value, f"{name_value} {exist_value} not as expected: {expected_value}"
#             if files_in_response is not None:
#                 for file in files_in_response:
#                     assert file in all_files_in_folder, f"Can't find: {file} in files folder: {FILES_DIR}"
#             await log.ainfo(
#                 f"SCENARIO: _{scenario_number}_ info: {name}",
#                 files_attached_before=attached_files_paths_before,
#                 files_attached_expected=expected.get("files_attached"),
#                 files_in_db=files_in_db,
#                 files_in_response=files_in_response,
#                 file_paths=file_paths,
#                 login_data=login,
#                 params=params,
#                 response=response.json(),
#                 suspension_files_expected=set(expected.get("suspension_files")),
#                 wings_of_end=f"______________ END of SCENARIO: ___ {scenario_number} ____ __{name} _______"
#             )
#     await delete_files_in_folder(file_paths)
#     await clean_test_database(async_db, User, Suspension, FileAttached, SuspensionsFiles)


async def test_user_get_all_tasks_url(
        async_client: AsyncClient,
        async_db: AsyncSession,
        tasks_orm: Task,
) -> None:
    """
    Тестирует возможность получения всех задач: pytest -k test_user_get_all_tasks_url -vs

    before_patched - параметры задачи при ее создании: тождественны "scenarios" из tasks_orm в confest.py

    scenarios - тестовые сценарии редактирования задачи (сценарии не изолированы друг от друга).
    Параметры задач не сбрасываются на базовые ("scenarios" из tasks_orm в confest.py) в цикле сценариев,
    поэтому используем разные сценарии при тестировании редактирования параметров задачи.

    expected - словарь ожидаемых значений задачи:
    если в эндпоинте параметр меняется, то изменяется значение и в словаре, либо берется из БД (при создании задачи).

    match_values - кортеж параметров, используемых в assert (ожидание - реальность).

    """
    test_url = TASKS_PATH + MAIN_ROUTE  # /api/tasks/
    user_orm_login = {"username": "user_fixture@f.com", "password": "testings"}
    scenario_number = 0
    scenarios = (
        # login, status, name
        (user_orm_login, 200, "get_all"),  # 1
    )
    async with async_client as ac:
        for login, status, name in scenarios:
            scenario_number += 1
            await log.ainfo(f"*************  SCENARIO: ___ {scenario_number} ___  *****  {name}  *************")
            response_login_user = await ac.post(LOGIN, data=login)
            response = await ac.get(
                test_url,
                headers={"Authorization": f"Bearer {response_login_user.json()['access_token']}"},
            )
            assert response.status_code == status, (
                f"User: {login} couldn't get {test_url}. Response: {response.__dict__}"
            )
            if response.status_code != 200:
                await log.ainfo(
                    f"SCENARIO: _{scenario_number}_ info: {name}",
                    login_data=login,
                    response=response.json(),
                    status=response.status_code,
                    wings_of_end=f"STATUS: {response.status_code}___ END of SCENARIO: ___ {scenario_number}  __{name}"
                )
                continue
            for index in enumerate(tasks_orm):  # проводим сверки по каждому объекту фикстуры и в ответе response
                position = index[0] + 1
                fixture_object = [obj for obj in tasks_orm if obj.id == position][0]
                object_in_response = [obj for obj in response.json() if obj["id"] == position][0]
                # expected values in scenario - take original suspensions_orm
                task_manager = await async_db.scalar(select(User).where(User.id == fixture_object.user_id))
                executor = await async_db.scalar(select(User).where(User.id == fixture_object.executor_id))
                expected = {
                    "total_objects": len(tasks_orm),
                    "task_files": [],
                    "task": fixture_object.task,
                    "start": fixture_object.task_start.strftime(DATE_FORMAT),
                    "duration": (
                            (fixture_object.deadline - datetime.now().date()).total_seconds() / TASK_DURATION_RESPONSE
                    ),
                    "finish": fixture_object.deadline.strftime(DATE_FORMAT),
                    "description": fixture_object.description,
                    "tech_process": int(fixture_object.tech_process),
                    "user_id": fixture_object.user_id,
                    "user_email": task_manager.email,
                    "executor_email": executor.email,
                    "executor_id": fixture_object.executor_id,
                    "is_archived": fixture_object.is_archived,
                }
                # run asserts in a scenario:
                match_values = (
                    # name_value, expected_value, exist_value
                    ("Total tasks: ", expected.get("total_objects"), len(response.json())),
                    ("Task files: ", expected.get("task_files"), object_in_response[FILES_SET_TO]),
                    ("Task start: ", expected.get("start"), object_in_response[TASK_START]),
                    ("Task finish: ", expected.get("finish"), object_in_response[TASK_FINISH]),
                    ("Description: ", expected.get("description"), object_in_response[TASK_DESCRIPTION]),
                    (
                        "Tech process: ",
                        expected.get("tech_process"),
                        int(json.loads(settings.TECH_PROCESS).get(object_in_response.get(TECH_PROCESS)))
                    ),
                    ("Duration: ", expected.get("duration"), object_in_response.get(TASK_DURATION)),
                    ("user_email: ", expected.get("user_email"), object_in_response[USER_MAIL]),
                    ("executor_email: ", expected.get("executor_email"), object_in_response[TASK_EXECUTOR_MAIL]),
                    ("executor_id: ", expected.get("executor_id"), object_in_response[TASK_EXECUTOR]),
                    ("is_archived: ", expected.get("is_archived"), object_in_response["is_archived"]),
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
    await clean_test_database(async_db, User, Task, FileAttached, TasksFiles)


# async def test_user_get_my_suspension_url(
#         async_client: AsyncClient,
#         async_db: AsyncSession,
#         suspensions_orm: Suspension,
# ) -> None:
#     """
#     Тестирует возможность получения всех случаев простоя:
#     pytest -k test_user_get_my_suspension_url -vs
#
#     before_patched - параметры простоя при его создании: тождественны "scenarios" из suspensions_orm в confest.py
#
#     scenarios - тестовые сценарии редактирования простоев (сценарии не изолированы друг от друга).
#     Параметры простоев не сбрасываются на базовые ("scenarios" из suspensions_orm в confest.py) в цикле сценариев,
#     поэтому используем разные сценарии при тестировании редактирования параметров простая.
#
#     expected - словарь ожидаемых значений параметров простоя:
#     если в эндпоинте параметр меняется, то изменяется значение и в словаре, либо берется из БД (при создании простоя).
#
#     match_values - кортеж параметров, используемых в assert (ожидание - реальность).
#
#     """
#     test_url = SUSPENSIONS_PATH + MY_SUSPENSIONS  # /api/suspensions/my_suspensions
#     user_orm_login = {"username": "user_fixture@f.com", "password": "testings"}
#     user_settings_email = json.loads(settings.STAFF)["1"]
#     user_settings_login = {"username": user_settings_email, "password": "testings"}
#     scenario_number = 0
#     scenarios = (
#         # login, status, name
#         (user_orm_login, 200, "get_user_orm_suspensions"),  # 1
#         (user_settings_login, 200, "get_user_settings_suspensions"),  # 2
#     )
#     async with async_client as ac:
#         for login, status, name in scenarios:
#             scenario_number += 1
#             await log.ainfo(f"*************  SCENARIO: ___ {scenario_number} ___  *****  {name}  *************")
#             response_login_user = await ac.post(LOGIN, data=login)
#             response = await ac.get(
#                 test_url,
#                 headers={"Authorization": f"Bearer {response_login_user.json()['access_token']}"},
#             )
#             assert response.status_code == status, (
#                 f"User: {login} couldn't get {test_url}. Response: {response.__dict__}"
#             )
#             if response.status_code != 200:
#                 await log.ainfo(
#                     f"SCENARIO: _{scenario_number}_ info: {name}",
#                     login_data=login,
#                     response=response.json(),
#                     status=response.status_code,
#                     wings_of_end=f"STATUS: {response.status_code}___ END of SCENARIO: ___ {scenario_number}  __{name}"
#                 )
#                 continue
#             current_user = await async_db.scalar(select(User).where(User.email == login.get("username")))
#             objects_by_user = await async_db.scalars(select(Suspension).where(Suspension.user_id == current_user.id))
#             objects_by_user_in_db = objects_by_user.all()
#             for user_object in objects_by_user_in_db:
#                 object_in_response = [obj for obj in response.json() if obj["id"] == user_object.id][0]
#                 expected = {
#                     "total_objects": len(objects_by_user_in_db),
#                     "suspension_files": [],
#                     "start": user_object.suspension_start.strftime(DATE_TIME_FORMAT),
#                     "finish": user_object.suspension_finish.strftime(DATE_TIME_FORMAT),
#                     "description": user_object.description,
#                     "measures": user_object.implementing_measures,
#                     "risk_accident": user_object.risk_accident,
#                     "tech_process": int(user_object.tech_process),
#                     "user_id": user_object.user_id,
#                 }
#             # run asserts in a scenario:
#                 match_values = (
#                     # name_value, expected_value, exist_value
#                     ("Total suspensions: ", expected.get("total_objects"), len(response.json())),
#                     # ("Suspension files: ", expected.get("suspension_files"), object_in_response[FILES_SET_TO]),
#                     ("Suspension start: ", expected.get("start"), object_in_response[SUSPENSION_START]),
#                     ("Suspension finish: ", expected.get("finish"), object_in_response[SUSPENSION_FINISH]),
#                     ("Description: ", expected.get("description"), object_in_response[SUSPENSION_DESCRIPTION]),
#                     ("Implementing measures: ", expected.get("measures"), object_in_response[IMPLEMENTING_MEASURES]),
#                     ("Risk accident: ", expected.get("risk_accident"), object_in_response[RISK_ACCIDENT]),
#                     (
#                         "Tech process: ",
#                         expected.get("tech_process"),
#                         int(json.loads(settings.TECH_PROCESS).get(object_in_response.get(TECH_PROCESS)))
#                     ),
#                     (
#                         "Duration: ",
#                         round(
#                             (user_object.suspension_finish
#                                 - user_object.suspension_start).total_seconds() / SUSPENSION_DURATION_RESPONSE, 1
#                         ),
#                         round(object_in_response.get(SUSPENSION_DURATION), 1)
#                     ),
#                     ("user_id: ", expected.get("user_id"), object_in_response[USER_ID]),
#                 )
#                 for name_value, expected_value, exist_value in match_values:
#                     assert expected_value == exist_value, (
#                         f"{name_value} {exist_value} not as expected: {expected_value}"
#                     )
#             await log.ainfo(
#                 f"SCENARIO: _{scenario_number}_ info: {name}",
#                 login_data=login,
#                 response=response.json(),
#                 wings_of_end=f"______________ END of SCENARIO: ___ {scenario_number} ____ __{name} _______"
#             )
#     await clean_test_database(async_db, User, Suspension, FileAttached, SuspensionsFiles)
#
#
# async def test_super_user_add_files_to_suspension_url(
#         async_client: AsyncClient,
#         async_db: AsyncSession,
#         suspensions_orm: Suspension,
#         super_user_orm: User
# ) -> None:
#     """
#     Тестирует добавление супер-пользователем к случаю простоя id файлов из формы:
#     pytest -k test_super_user_add_files_to_suspension_url -vs
#
#     before_patched - параметры простоя при его создании: тождественны "scenarios" из suspensions_orm в confest.py
#
#     scenarios - тестовые сценарии редактирования простоев (сценарии не изолированы друг от друга).
#     Параметры простоев не сбрасываются на базовые ("scenarios" из suspensions_orm в confest.py) в цикле сценариев,
#     поэтому используем разные сценарии при тестировании редактирования параметров простая.
#
#     expected - словарь ожидаемых значений параметров простоя:
#     если в эндпоинте параметр меняется, то изменяется значение и в словаре, либо берется из БД (при создании простоя).
#
#     match_values - кортеж параметров, используемых в assert (ожидание - реальность).
#
#     """
#     test_url = SUSPENSIONS_PATH + ADD_FILES_TO_SUSPENSION  # /api/suspensions/add_files_to_suspension
#     download_files_url = FILES_PATH + DOWNLOAD_FILES  # /api/files/download_files
#     user_orm_login = {"username": "user_fixture@f.com", "password": "testings"}
#     super_user_login = {"username": super_user_orm.email, "password": "testings"}
#     test_files = ["testfile.txt", "testfile2.txt", "testfile3.txt"]
#     await create_test_files(test_files)
#     scenario_number = 0
#     patched_objects = set()
#     files_to_delete_at_the_end = []
#     # Сценарии завязаны друг на друга - не изолированы!
#     scenarios = (
#         # login, params, status, file_index, name
#         (user_orm_login, {'suspension_id': 1, SET_FILES_LIST_TO_SUSPENSION: [1]}, 403, 0, "s1 not admin"),  # 1
#         (super_user_login, {'suspension_id': 1, SET_FILES_LIST_TO_SUSPENSION: [1]}, 200, 0, "s1 add file_id 1"),  # 2
#         (super_user_login, {'suspension_id': 1, SET_FILES_LIST_TO_SUSPENSION: [2]}, 200, 1, "s1 add file_id 2"),  # 3
#         (super_user_login, {'suspension_id': 1, SET_FILES_LIST_TO_SUSPENSION: [1, 2]}, 200, 2, "s1 files: 1,2"),  # 4
#         (super_user_login, {'suspension_id': 2, SET_FILES_LIST_TO_SUSPENSION: [1, 2, 3]}, 200, 2, "s2 files: 1,2,3"),
#         (super_user_login, {'suspension_id': 3, SET_FILES_LIST_TO_SUSPENSION: [1, 2, 3, 4, 5]}, 200, 2, "s3 5 files"),
#     )
#     async with async_client as ac:
#         for login, create_params, status, file_index, name in scenarios:
#             scenario_number += 1
#             await log.ainfo(f"*************  SCENARIO: ___ {scenario_number} ___  ***** {name}  ***************")
#             # gather objects in db info before testing:
#             suspension_id = create_params.get('suspension_id')
#             suspension_files_object_before = await async_db.scalars(select(SuspensionsFiles))
#             suspension_files_in_db_before = suspension_files_object_before.all()
#             if suspension_files_in_db_before:
#                 suspension_files_records_before = [
#                     (record.suspension_id, record.file_id) for record in suspension_files_in_db_before
#                 ]
#             else:
#                 suspension_files_records_before = []
#             response_login_super_user = await ac.post(LOGIN, data=super_user_login)  # only super_user is allowed!
#             assert response_login_super_user.status_code == 200, f"Super_user: {super_user_login} can't get {LOGIN}"
#             # downloading files with api to test it in scenarios
#             download_files_response = await ac.post(
#                 download_files_url,
#                 files={"files": open(TEST_ROUTES_DIR.joinpath(test_files[file_index]), "rb")},
#                 headers={"Authorization": f"Bearer {response_login_super_user.json()['access_token']}"},
#             )
#             assert download_files_response.status_code == 200, (
#                 f"User: {super_user_login} can't get {download_files_url} Response: {download_files_response.__dict__}"
#             )
#             file_objects = await async_db.scalars(select(FileAttached))
#             files_in_db = file_objects.all()
#             file_names_in_scenario = [
#                 file.name for file in files_in_db if file.id in create_params.get(SET_FILES_LIST_TO_SUSPENSION)
#             ]
#             files_downloaded_response = download_files_response.json().get(FILES_WRITTEN_DB)
#             file_names_added = [file_dict.get("Имя файла.") for file_dict in files_downloaded_response]
#             response_login_user = await ac.post(LOGIN, data=login)  # файлы добавлены, можно начинать тесты
#             response = await ac.post(
#                 test_url,
#                 params=create_params,
#                 headers={"Authorization": f"Bearer {response_login_user.json()['access_token']}"},
#             )
#             assert response.status_code == status, f"User: {login} can't get {test_url}. Response: {response.__dict__}"
#             if response.status_code != 200:
#                 await log.ainfo(
#                     f"SCENARIO: ___ status_code != 200___ _{scenario_number}_ info: {name}",
#                     files_in_db=files_in_db,
#                     login_data=login,
#                     params=create_params,
#                     response=response.json(),
#                     status=response.status_code,
#                     wings_of_end=f"STATUS: {response.status_code}___ END of SCENARIO: ___ {scenario_number}  _{name}_"
#                 )
#                 await delete_files_in_folder(
#                     [FILES_DIR.joinpath(file_name) for file_name in file_names_added if file_names_added is not None]
#                 )
#                 await clean_test_database(async_db, FileAttached)  # clean data after failed scenario
#                 continue
#             # patched suspensions:
#             patched_objects.add(suspension_id)  # множество файлов в обработке для asserts suspension_files_in_scenario
#             objects = await async_db.scalars(select(Suspension))
#             objects_in_db = objects.all()
#             object_in_db = [obj for obj in objects_in_db if obj.id == suspension_id][0]
#             # patched files:
#             file_objects = await async_db.scalars(select(FileAttached))  # == [] when no files attached
#             files_in_db = file_objects.all() if file_objects is not None else []
#             file_paths = [
#                 FILES_DIR.joinpath(file_name) for file_name in file_names_added if file_names_added is not None
#             ]
#             files_to_delete_at_the_end += file_paths
#             all_files_in_folder = [file.name for file in FILES_DIR.glob('*')]
#             # patched suspension_files:
#             suspension_files_object = await async_db.scalars(select(SuspensionsFiles))
#             suspension_files_in_db = suspension_files_object.all()
#             suspension_files_records = set(
#                 ((record.suspension_id, record.file_id) for record in suspension_files_in_db)
#             )
#             suspension_files_in_scenario = set(
#                 ((suspension_id, file_id) for file_id in create_params.get(SET_FILES_LIST_TO_SUSPENSION))
#             )
#             # run asserts in a scenario:
#             expected = {
#                 "files_attached": await get_file_names_for_model_db(async_db, Suspension, object_in_db.id),
#                 "suspension_files":
#                     suspension_files_in_scenario.union(suspension_files_records_before)
#                     if len(patched_objects) > 1 else suspension_files_in_scenario,
#             }
#             match_values = (
#                 # name_value, expected_value, exist_value
#                 ("Suspension id: ", suspension_id, object_in_db.id),
#                 ("Attached files: ", set(expected.get("files_attached")), set(file_names_in_scenario)),
#                 ("Suspension files: ", expected.get("suspension_files"), suspension_files_records),
#                 # (": ",),  # more scenarios
#             )
#             for name_value, expected_value, exist_value in match_values:
#                 assert expected_value == exist_value, f"{name_value} {exist_value} not as expected: {expected_value}"
#             if file_names_added is not None:
#                 for file in file_names_added:
#                     assert file in all_files_in_folder, f"Can't find: {file} in files folder: {FILES_DIR}"
#             await log.ainfo(
#                 f"SCENARIO: _{scenario_number}_ info: {name}",
#                 files_in_db=files_in_db,
#                 file_names_added=file_names_added,
#                 login_data=login,
#                 params=create_params,
#                 response=response.json(),
#                 suspension_files_expected=suspension_files_in_scenario,
#                 suspension_files_in_db=suspension_files_records,
#                 wings_of_end=f"_______________________________________________ END of SCENARIO: ___ {scenario_number}"
#             )
#     await clean_test_database(async_db, User, Suspension, FileAttached, SuspensionsFiles)
#     await delete_files_in_folder(files_to_delete_at_the_end)
#
#
# async def test_super_user_delete_suspension_url(
#         async_client: AsyncClient,
#         async_db: AsyncSession,
#         suspensions_orm: Suspension,
#         super_user_orm: User
# ) -> None:
#     """
#     Тестирует удаление супер-пользователем случая простоя по id из формы:
#     pytest -k test_super_user_delete_suspension_url -vs
#
#     before_patched - параметры простоя при его создании: тождественны "scenarios" из suspensions_orm в confest.py
#
#     scenarios - тестовые сценарии редактирования простоев (сценарии не изолированы друг от друга).
#     Параметры простоев не сбрасываются на базовые ("scenarios" из suspensions_orm в confest.py) в цикле сценариев,
#     поэтому используем разные сценарии при тестировании редактирования параметров простая.
#
#     expected - словарь ожидаемых значений параметров простоя:
#     если в эндпоинте параметр меняется, то изменяется значение и в словаре, либо берется из БД (при создании простоя).
#
#     match_values - кортеж параметров, используемых в assert (ожидание - реальность).
#
#     """
#     test_url = SUSPENSIONS_PATH + "/"  # /api/suspensions/{suspension_id}
#     download_files_url = FILES_PATH + DOWNLOAD_FILES  # /api/files/download_files
#     user_orm_login = {"username": "user_fixture@f.com", "password": "testings"}
#     super_user_login = {"username": super_user_orm.email, "password": "testings"}
#     test_files = ["testfile.txt", "testfile2.txt", "testfile3.txt"]
#     files_list_set_to_suspension = [1]
#     await create_test_files(test_files)
#     scenario_number = 0
#     files_to_delete_at_the_end = []
#     scenarios = (
#         # login, params, status, file_index, name, add_file_to_suspension_id
#         (user_orm_login, {'suspension_id': 1}, 403, 0, "s1 not admin", 1),  # 1
#         (super_user_login, {'suspension_id': 1}, 200, 0, "delete s1", 1),  # 2
#         (super_user_login, {'suspension_id': 1}, 404, 0, "can't delete s1 again", 2),  # 3
#         (super_user_login, {'suspension_id': 2}, 200, 0, "delete s2 with 2 files", 2),  # 4
#     )
#     async with async_client as ac:
#         for login, create_params, status, file_index, name, add_file_to_suspension_id in scenarios:
#             scenario_number += 1
#             await log.ainfo(f"*************  SCENARIO: ___ {scenario_number} ___  ***** {name}  ***************")
#             # GATHER objects in db info before testing:
#             suspension_id = create_params.get('suspension_id')
#             suspension_files_object_before = await async_db.scalars(select(SuspensionsFiles))
#             suspension_files_in_db_before = suspension_files_object_before.all()
#             response_login_super_user = await ac.post(LOGIN, data=super_user_login)  # only super_user is allowed!
#             assert response_login_super_user.status_code == 200, f"Super_user: {super_user_login} can't get {LOGIN}"
#             # DOWNLOAD files through api to test removing files along with suspension
#             download_files_response = await ac.post(
#                 download_files_url,
#                 files={"files": open(TEST_ROUTES_DIR.joinpath(test_files[file_index]), "rb")},
#                 headers={"Authorization": f"Bearer {response_login_super_user.json()['access_token']}"},
#             )
#             assert download_files_response.status_code == 200, (
#                 f"User: {super_user_login} can't get {download_files_url} Response: {download_files_response.__dict__}"
#             )
#             set_files_response = await ac.post(
#                 SUSPENSIONS_PATH + ADD_FILES_TO_SUSPENSION,
#                 params={
#                     'suspension_id': add_file_to_suspension_id,
#                     SET_FILES_LIST_TO_SUSPENSION: files_list_set_to_suspension
#                 },
#                 headers={"Authorization": f"Bearer {response_login_super_user.json()['access_token']}"},
#             )
#             assert set_files_response.status_code == 200, (
#                 f"User: {login} can't get {test_url}. Response: {set_files_response.__dict__}"
#             )
#             files_downloaded_response = download_files_response.json().get(FILES_WRITTEN_DB)
#             file_names_added = [file_dict.get("Имя файла.") for file_dict in files_downloaded_response]
#             all_files_in_folder = [file.name for file in FILES_DIR.glob('*')]
#             if file_names_added is not None:
#                 for file in file_names_added:
#                     assert file in all_files_in_folder, f"Can't find: {file} in files folder: {FILES_DIR}"
#             # START TESTINGS WITH FILES ATTACHED!
#             objects = await async_db.scalars(select(Suspension))
#             objects_in_db = objects.all()
#             object_in_db = [obj for obj in objects_in_db if obj.id == suspension_id]
#             # patched files:
#             file_objects = await async_db.scalars(select(FileAttached))  # == [] when no files attached
#             files_in_db = file_objects.all() if file_objects is not None else []
#             file_paths = [
#                 FILES_DIR.joinpath(file_name) for file_name in file_names_added if file_names_added is not None
#             ]
#             files_to_delete_at_the_end += file_paths
#             response_login_user = await ac.post(LOGIN, data=login)
#             response = await ac.delete(
#                 test_url + f"{suspension_id}",
#                 params=create_params,
#                 headers={"Authorization": f"Bearer {response_login_user.json()['access_token']}"},
#             )
#             assert response.status_code == status, f"User: {login} can't get {test_url}. Response: {response.__dict__}"
#             if response.status_code != 200:
#                 await log.ainfo(
#                     f"SCENARIO: ___ status_code != 200___ _{scenario_number}_ info: {name}",
#                     files_in_db=files_in_db,
#                     login_data=login,
#                     params=create_params,
#                     response=response.json(),
#                     status=response.status_code,
#                     wings_of_end=f"STATUS: {response.status_code}___ END of SCENARIO: ___ {scenario_number}  _{name}_"
#                 )
#                 await delete_files_in_folder(
#                     [FILES_DIR.joinpath(file_name) for file_name in file_names_added if file_names_added is not None]
#                 )
#                 await clean_test_database(async_db, FileAttached, SuspensionsFiles)  # clean data after failed scenario
#                 continue
#             # run asserts in a scenario:
#             # GATHER objects in db info after testing:
#             objects_after = await async_db.scalars(select(Suspension))
#             objects_in_db_after = objects_after.all()
#             object_in_db_after = [obj for obj in objects_in_db_after if obj.id == suspension_id]
#             file_objects_after = await async_db.scalars(select(FileAttached))  # == [] when no files attached
#             files_in_db_after = file_objects_after.all() if file_objects_after is not None else []
#             file_in_db_after = [obj for obj in files_in_db_after if obj.id == files_list_set_to_suspension[0]]
#             suspension_files_object_after = await async_db.scalars(select(SuspensionsFiles))
#             suspension_files_in_db_after = suspension_files_object_after.all()
#             all_files_in_folder = [file.name for file in FILES_DIR.glob('*')]
#             if file_names_added is not None:
#                 for file in file_names_added:
#                     assert file not in all_files_in_folder, f"{file} in files folder: {FILES_DIR}, but shouldn't"
#             expected = {
#                 "suspensions_after": len(objects_in_db) - 1,
#                 "suspension_id_in_db": [],
#                 "file_in_db": [],
#             }
#             match_values = (
#                 # name_value, expected_value, exist_value
#                 ("Suspension id: ", suspension_id, object_in_db[0].id),
#                 ("Total suspensions after: ", expected.get("suspensions_after"), len(objects_in_db_after)),
#                 ("No object in db: ", expected.get("suspension_id_in_db"), object_in_db_after),
#                 ("No file attached in db: ", expected.get("file_in_db"), file_in_db_after),
#                 ("No file relations in db: ", suspension_files_in_db_before, suspension_files_in_db_after),
#             )
#             for name_value, expected_value, exist_value in match_values:
#                 assert expected_value == exist_value, f"{name_value} {exist_value} not as expected: {expected_value}"
#             await log.ainfo(
#                 f"SCENARIO: _{scenario_number}_ info: {name}",
#                 files_in_db=files_in_db,
#                 file_names_added=file_names_added,
#                 files_in_db_after=files_in_db_after,
#                 objects_in_db=objects_in_db,
#                 objects_in_db_after=objects_in_db_after,
#                 login_data=login,
#                 params=create_params,
#                 response=response.json(),
#                 suspension_files_in_db_after=suspension_files_in_db_after,
#                 suspension_files_in_db_before=suspension_files_in_db_before,
#                 wings_of_end=f"_______________________________________________ END of SCENARIO: ___ {scenario_number}"
#             )
#     await clean_test_database(async_db, User, Suspension, FileAttached, SuspensionsFiles)
#     await delete_files_in_folder(files_to_delete_at_the_end)
