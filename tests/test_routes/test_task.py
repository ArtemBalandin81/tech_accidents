"""
Асинхронные тесты работы эндпоинтов задач: tests/test_routes/test_task.py
pytest -s -W ignore::DeprecationWarning
pytest -k test_unauthorized_get_urls -vs
pytest -k test_task.py -vs  # тесты только из этого файла
pytest -vs  # все тесты
https://anyio.readthedocs.io/en/stable/testing.html

pytest -k test_unauthorized_tries_task_urls -vs
pytest -k test_user_get_task_url -vs
pytest -k test_user_get_all_tasks_url -vs
pytest -k test_user_get_all_tasks_opened_url -vs
pytest -k test_user_get_my_tasks_ordered_url -vs
pytest -k test_user_get_my_tasks_todo_url -vs Todo /api/tasks/my_tasks_todo
pytest -k test_user_post_task_form_url -vs
pytest -k test_user_post_task_with_files_form_url -vs
pytest -k test_user_patch_task_url -vs
pytest -k test_super_user_delete_task_url -vs

pytest -k test_super_user_add_files_to_task_url -vs

Для отладки рекомендуется использовать:
print(f'response_dir: {dir(response)}')
print(f'RESPONSE__dict__: {response.__dict__}')

"""
import json
import os
import sys
from copy import deepcopy
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


async def test_user_patch_task_url(
        async_client: AsyncClient,
        async_db: AsyncSession,
        tasks_orm: Task,
        super_user_orm: User
) -> None:
    """
    Тестирует редактирование задачи из формы с возможностью дозагрузки файла:
    pytest -k test_user_patch_task_url -vs

    before_patched - параметры задачи при ее создании: тождественны "scenarios" из tasks_orm в confest.py

    scenarios - тестовые сценарии использования эндпоинта (сценарии не изолированы друг от друга).
    expected - словарь ожидаемых значений в сценарии.
    match_values - кортеж параметров, используемых в assert (ожидание - реальность).

    """
    test_url = TASKS_PATH + "/"  # /api/tasks/{task_id}
    user_orm_email = "user_fixture@f.com"
    user_orm_login = {"username": user_orm_email, "password": "testings"}
    user_settings_email = json.loads(settings.STAFF)["1"]
    user_settings_login = {"username": user_settings_email, "password": "testings"}
    super_user_login = {"username": super_user_orm.email, "password": "testings"}
    day_ago = (datetime.now(TZINFO) - timedelta(days=1)).strftime(DATE_FORMAT)
    tomorrow = (datetime.now(TZINFO) + timedelta(days=1)).strftime(DATE_FORMAT)
    error_in_date = "11-07-20244"
    test_files = ["testfile.txt", "testfile2.txt", "testfile3.txt"]
    await create_test_files(test_files)
    user_from_settings = await async_db.scalar(select(User).where(User.email == user_settings_email))
    user_orm = await async_db.scalar(select(User).where(User.email == user_orm_email))
    scenario_number = 0
    scenarios = (
        # login, params, status, uploaded_file, file_index, task_id, name - Dependant scenarios !!!
        (user_settings_login, {TASK_FINISH: error_in_date}, 422, None, None, 1, "error_in_date"),  # 1
        (user_settings_login, {TASK_FINISH: day_ago}, 422, None, None, 2, "L > R: -1_[0] deadline < task start"),  # 2
        (user_orm_login, {TASK_DESCRIPTION: "not author or admin"}, 403, None, None, 2, "not author or admin"),  # 3
        (super_user_login, {TASK_EXECUTOR_MAIL: user_orm.email}, 422, None, None, 2, "executor not from ENUM"),  # 4
        (
            super_user_login,
            {TASK_DESCRIPTION: "admin changes an executor obj_id=3", TASK_EXECUTOR_MAIL: user_from_settings.email},
            200, None, None, 3, "admin changes an executor obj_id=3"
        ),  # 5
        (
            super_user_login,
            {TASK_DESCRIPTION: "admin changes an executor & upload f.", TASK_EXECUTOR_MAIL: user_from_settings.email},
            200, {"file_to_upload": open(TEST_ROUTES_DIR.joinpath(test_files[2]), "rb")}, 2, 3, "admin change executor"
        ),  # 6 ['<Obj 3 - Files 1>']
        (
            user_orm_login,
            {
            TASK_FINISH: tomorrow,
            TASK: "4 edited",
            TASK_DESCRIPTION: "tomorrow edited",
            IS_ARCHIVED: True,
            TECH_PROCESS: json.loads(settings.TECH_PROCESS)["SPEC_DEP_26"],
            TASK_EXECUTOR_MAIL: user_from_settings.email,
            IMPLEMENTING_MEASURES: "aLL possible parameters have been changed & file is uploaded",
            FILES_UNLINK: False
            },
            200, {"file_to_upload": open(TEST_ROUTES_DIR.joinpath(test_files[0]), "rb")}, 0, 4, "all parameters & file"
        ),  # 7 ['<Obj 3 - Files 1>', '<Obj 4 - Files 2>']
        (
            user_settings_login,
            {TASK_DESCRIPTION: "unlink if no files", FILES_UNLINK: True},
            200, None, None, 1, "unlink if no files in task_id = 1, but ['<Obj 3 - Files 1>', '<Obj 4 - Files 2>']"
        ),  # 8 ['<Obj 3 - Files 1>', '<Obj 4 - Files 2>']
        (user_settings_login, {}, 200, None, None, 1, "empty params in task_id = 1 edited"),  # 9
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
        for login, create_params, status, uploaded_file, file_index, task_id, name in scenarios:
            scenario_number += 1
            await log.ainfo(f"**************************************  SCENARIO: __ {scenario_number} __: {name}")
            # grab info of objects in db before testing:
            objects_before = await async_db.scalars(select(Task))
            objects_in_db_before = objects_before.all()  # objects before scenarios have started
            object_before_to_patch = [_ for _ in objects_in_db_before if _.id == task_id][0]
            # file_names_attached_before:
            file_names_attached = await get_file_names_for_model_db(async_db, Task, task_id)
            file_names_attached_before = (
                [file.split("_")[-1] for file in file_names_attached if len(file_names_attached) > 0]
            )
            attached_files_paths_before = [
                FILES_DIR.joinpath(name) for name in file_names_attached if file_names_attached is not None
            ]
            # task_files objects before:
            task_files_object_before = await async_db.scalars(select(TasksFiles))  # all task_files objects
            task_files_in_db_before = task_files_object_before.all()
            object_id_task_files_before = await async_db.scalars(
                select(TasksFiles)
                .where(TasksFiles.task_id == task_id)
            )
            object_id_task_files_before_all = object_id_task_files_before.all()  # task_files attached to the object_id
            # starting test scenarios:
            response_login_user = await ac.post(LOGIN, data=login)
            response = await ac.patch(
                test_url + f"{task_id}",
                params=create_params,
                headers={"Authorization": f"Bearer {response_login_user.json()['access_token']}"},
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
                        "orm_start": object_before_to_patch.task_start.strftime(DATE_FORMAT),
                        "orm_finish": object_before_to_patch.deadline.strftime(DATE_FORMAT),
                        "duration": (object_before_to_patch.deadline - object_before_to_patch.task_start),
                        "task_files": task_files_in_db_before,
                    },
                    params=create_params,
                    response=response.json(),
                    status=response.status_code,
                    wings_of_end=f"STATUS: {response.status_code}___ END of SCENARIO: ___ {scenario_number}  _{name}_"
                )
                continue
            # patched tasks:
            objects = await async_db.scalars(select(Task))
            objects_in_db = objects.all()
            object_in_db = [_ for _ in objects_in_db if _.id == task_id][0]
            # attached files:
            attached_files_objects = await async_db.scalars(
                select(FileAttached)
                .join(Task.files)
                .where(Task.id == task_id)
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
            task_files_object = await async_db.scalars(select(TasksFiles))
            task_files_in_db = task_files_object.all()
            if uploaded_file and (create_params.get(FILES_UNLINK) is not True):
                task_files_expected = [str(record) for record in task_files_in_db_before]
                # get file_id by its name, and make '<Task 3 - Files 1>' в task_files_expected
                task_files_expected.append(f'<Task {task_id} - Files {new_file_object[0].id}>')
                file_names_attached_expected = file_names_attached
                file_names_attached_expected.append(new_file_name_in_response[0])
            elif create_params.get(FILES_UNLINK):
                file_names_attached_expected = []
                task_files_expected = [record for record in task_files_in_db_before]
                task_files_expected = set(task_files_expected).difference(set(object_id_task_files_before_all))  # del task_files for task_id
            else:
                file_names_attached_expected = file_names_attached_before
                task_files_expected = task_files_in_db_before
            task_manager = await async_db.scalar(select(User).where(User.email == login.get("username")))
            if create_params.get(TASK_EXECUTOR_MAIL) is not None:
                executor = await async_db.scalar(
                    select(User).where(User.email == create_params.get(TASK_EXECUTOR_MAIL))
                )
            else:
                executor = await async_db.scalar(select(User).where(User.id == object_before_to_patch.executor_id))
            expected = {  # expected values in scenario
                "total_tasks_expected": len(objects_in_db_before),
                "task_expected_id": task_id,
                "start": (
                    create_params.get(TASK_START) if create_params.get(TASK_START) is not None
                    else object_before_to_patch.task_start.strftime(DATE_FORMAT)
                ),
                "finish": (
                    create_params.get(TASK_FINISH) if create_params.get(TASK_FINISH) is not None
                    else object_before_to_patch.deadline.strftime(DATE_FORMAT)
                ),
                "task": (
                    create_params.get(TASK) if create_params.get(TASK) is not None
                    else object_before_to_patch.task
                ),
                "description": (
                    create_params.get(TASK_DESCRIPTION) if create_params.get(TASK_DESCRIPTION) is not None
                    else object_before_to_patch.description
                ),
                "tech_process": (
                    create_params.get(TECH_PROCESS) if create_params.get(TECH_PROCESS) is not None
                    else object_before_to_patch.tech_process
                ),
                "is_archived": (
                    create_params.get(IS_ARCHIVED) if create_params.get(IS_ARCHIVED) is not None
                    else object_before_to_patch.is_archived
                ),
                "user_id": task_manager.id,
                "executor_id": executor.id,
                "files_attached": file_names_attached_expected,  # загружаемый + имеющийся в БД
                "task_files": [str(record) for record in task_files_expected],
            }
            # run asserts in a scenario:
            match_values = (
                # name_value, expected_value, exist_value
                ("Task id: ", expected.get("task_expected_id"), object_in_db.id),
                ("Total tasks: ", expected.get("total_tasks_expected"), len(objects_in_db)),
                ("Attached files: ", expected.get("files_attached"), file_names_attached),
                ("Task files: ", set(expected.get("task_files")), set([str(record) for record in task_files_in_db])),
                ("Task start: ", expected.get("start"), object_in_db.task_start.strftime(DATE_FORMAT)),
                ("Task finish: ", expected.get("finish"), object_in_db.deadline.strftime(DATE_FORMAT)),
                ("Task: ", expected.get("task"), object_in_db.task),
                ("Description: ", expected.get("description"), object_in_db.description),
                ("Tech_process: ", int(expected.get("tech_process")), object_in_db.tech_process),
                ("is_archived: ", int(expected.get("is_archived")), object_in_db.is_archived),
                (
                    "Duration: ",
                    (
                            datetime.strptime(expected["finish"], DATE_FORMAT)
                            - datetime.strptime(expected["start"], DATE_FORMAT)
                    ),
                    object_in_db.deadline - object_in_db.task_start
                ),
                ("user_id: ", expected.get("user_id"), object_in_db.user_id),
                ("executor_id: ", expected.get("executor_id"), object_in_db.executor_id),
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
                    "orm_description": object_before_to_patch.description,
                    "orm_start": object_before_to_patch.task_start.strftime(DATE_FORMAT),
                    "orm_finish": object_before_to_patch.deadline.strftime(DATE_FORMAT),
                    "duration": (object_before_to_patch.deadline - object_before_to_patch.task_start),
                    "task_files": task_files_in_db_before,
                },
                params=create_params,
                response=response.json(),
                task_files_in_db=task_files_in_db,
                wings_of_end=f"_______________________________________________ END of SCENARIO: ___ {scenario_number}"
            )
    # if files are not deleted in folder - it means, that scenario of "files unlink" doesn't work correctly
    await clean_test_database(async_db, User, Task, FileAttached, TasksFiles)  # files are deleted in api


async def test_user_post_task_with_files_form_url(
        async_client: AsyncClient,
        async_db: AsyncSession,
        user_orm: User,
        user_from_settings: User,
) -> None:
    """
    Тестирует постановку задачи из формы с обязательной загрузкой нескольких файлов:
    pytest -k test_user_post_task_with_files_form_url -vs

    scenarios - тестовые сценарии использования эндпоинта (все сценарии изолированы).
    expected - словарь ожидаемых значений в сценарии.
    match_values - кортеж параметров, используемых в assert (ожидание - реальность).
    """
    test_url = TASKS_PATH + POST_TASK_FILES_FORM  # /api/tasks/post_task_with_files_form
    user_orm_login = {"username": "user_fixture@f.com", "password": "testings"}
    user_from_settings_login = {"username": "user@example.com", "password": "testings"}
    now = datetime.now(TZINFO).strftime(DATE_FORMAT)
    day_ago = (datetime.now(TZINFO) - timedelta(days=1)).strftime(DATE_FORMAT)
    tomorrow = (datetime.now(TZINFO) + timedelta(days=1)).strftime(DATE_FORMAT)
    error_in_date = "11-07-20244"
    test_files = ["testfile.txt", "testfile2.txt", "testfile3.txt"]
    await create_test_files(test_files)
    files = [
        ("files_to_upload", open(TEST_ROUTES_DIR.joinpath(test_files[0]), "rb")),
        ("files_to_upload", open(TEST_ROUTES_DIR.joinpath(test_files[1]), "rb")),
        ("files_to_upload", open(TEST_ROUTES_DIR.joinpath(test_files[2]), "rb"))
    ]
    scenario_number = 0
    scenarios = (
        # login, params, status, files, name
        (user_orm_login, {
            TASK_START: error_in_date,
            TASK_FINISH: day_ago,
            TASK: "1",
            TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
            TASK_DESCRIPTION: "error_in_date",
            TASK_EXECUTOR_MAIL: user_from_settings.email
            # TASK_EXECUTOR_MAIL_NOT_FROM_ENUM: None,
        }, 422, files, "error_in_date"),  # 1
        (user_orm_login, {
            TASK_START: now,
            TASK_FINISH: day_ago,
            TASK: "1",
            TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
            TASK_DESCRIPTION: "-1_[0]",
            TASK_EXECUTOR_MAIL: user_from_settings.email,
            # TASK_EXECUTOR_MAIL_NOT_FROM_ENUM: None,
        }, 422, files, "L > R: -1_[0] deadline < task start"),  # 2
        (user_orm_login, {
            TASK_START: now,
            TASK_FINISH: day_ago,
            TASK: "1",
            TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
            TASK_DESCRIPTION: "-1_[0]",
            TASK_EXECUTOR_MAIL: user_from_settings.email,
            # TASK_EXECUTOR_MAIL_NOT_FROM_ENUM: None,
        }, 422, None, "None - no files to upload"),  # 3
        (user_orm_login, {
            TASK_START: now,
            TASK_FINISH: day_ago,
            TASK: "1",
            TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
            TASK_DESCRIPTION: "-1_[0]",
            TASK_EXECUTOR_MAIL: user_from_settings.email,
            # TASK_EXECUTOR_MAIL_NOT_FROM_ENUM: None,
        }, 422, [], "[] - no files to upload"),  # 4
        (user_orm_login, {
            TASK_START: now,
            TASK_FINISH: tomorrow,
            TASK: "1",
            TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
            TASK_DESCRIPTION: "[0]_+1",
            TASK_EXECUTOR_MAIL: user_from_settings.email,
            # TASK_EXECUTOR_MAIL_NOT_FROM_ENUM: None,
        }, 200, files, "tomorrow deadline"),  # 5
        (user_from_settings_login, {
            TASK_START: now,
            TASK_FINISH: tomorrow,
            TASK: "1",
            TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
            TASK_DESCRIPTION: "[0]_+1",
            TASK_EXECUTOR_MAIL: user_from_settings.email,
            # TASK_EXECUTOR_MAIL_NOT_FROM_ENUM: None,
        }, 200, files, "tomorrow deadline for myself task"),  # 6
        (user_orm_login, {
            TASK_START: now,
            TASK_FINISH: tomorrow,
            TASK: "1",
            TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
            TASK_DESCRIPTION: "[0]_+1",
            TASK_EXECUTOR_MAIL: user_from_settings.email,
            TASK_EXECUTOR_MAIL_NOT_FROM_ENUM: user_from_settings.email,
        }, 200, files, "TASK_EXECUTOR_MAIL_NOT_FROM_ENUM BUT is ENUM"),  # 7
        (user_orm_login, {
            TASK_START: now,
            TASK_FINISH: tomorrow,
            TASK: "1",
            TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
            TASK_DESCRIPTION: "[0]_+1",
            TASK_EXECUTOR_MAIL: user_from_settings.email,
            TASK_EXECUTOR_MAIL_NOT_FROM_ENUM: user_orm.email,
        }, 200, files, "TASK_EXECUTOR_MAIL_NOT_FROM_ENUM == user_orm"),  # 8
    )
    async with async_client as ac:
        for login, create_params, status, files, name in scenarios:
            scenario_number += 1
            await log.ainfo(f"**************************************  SCENARIO: __ {scenario_number} __: {name}")
            response_login_user = await ac.post(LOGIN, data=login)
            response = await ac.post(
                test_url,
                params=create_params,
                headers={"Authorization": f"Bearer {response_login_user.json()['access_token']}"},
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
            # created tasks:
            objects = await async_db.scalars(select(Task))
            objects_in_db = objects.all()
            new_object = objects_in_db[0] if objects_in_db is not None else None
            total_objects = len(objects_in_db) if objects_in_db is not None else None
            # files attached:
            file_objects = await async_db.scalars(select(FileAttached))
            files_in_db = file_objects.all()
            files_in_response = response.json().get(FILES_SET_TO)
            files_attached = await get_file_names_for_model_db(async_db, Task, new_object.id)
            file_names_attached = [file.split("_")[-1] for file in files_attached if len(files_attached) > 0]
            all_files_in_folder = [file.name for file in FILES_DIR.glob('*')]
            file_paths = [
                FILES_DIR.joinpath(file_name) for file_name in files_in_response if files_in_response is not None
            ]
            task_manager = await async_db.scalar(select(User).where(User.email == login.get("username")))
            if create_params.get(TASK_EXECUTOR_MAIL_NOT_FROM_ENUM) is not None:
                executor = await async_db.scalar(
                    select(User).where(User.email == create_params.get(TASK_EXECUTOR_MAIL_NOT_FROM_ENUM))
                )
            else:
                executor = await async_db.scalar(
                    select(User).where(User.email == create_params.get(TASK_EXECUTOR_MAIL))
                )
            # created files relations:
            task_files_object = await async_db.scalars(select(TasksFiles))
            task_files_in_db = task_files_object.all()
            task_files_records = set(
                ((record.task_id, record.file_id) for record in task_files_in_db)
            ) if files else None
            expected = {  # expected values in scenario
                "total_objects_expected": 1,
                "task_expected_id": 1,  # could be response.json()["id"]
                "files_attached": set(test_files) if files else None,
                # "task_files": set(
                #     ((response.json()["id"], index[0] + 1) for index in enumerate(files_in_response))
                # ),  # actually is the same as in db, but smth else is needed todo
                "task_files": {(1, 1), (1, 2), (1, 3)} if files else None,  # just a plug - smth else is needed !!!
                "start": create_params.get(TASK_START),
                "finish": create_params.get(TASK_FINISH),
                "task": create_params.get(TASK),
                "description": create_params.get(TASK_DESCRIPTION),
                "tech_process": create_params.get(TECH_PROCESS),
                "is_archived": False,
                "user_id": task_manager.id,
                "executor_id": executor.id,
            }
            # run asserts in a scenario:
            match_values = (
                # name_value, expected_value, exist_value
                ("Task id: ", expected.get("task_expected_id"), new_object.id),
                ("Total tasks: ", expected.get("total_objects_expected"), total_objects),
                (
                    "Attached files: ",
                    expected.get("files_attached"),
                    set(file_names_attached)
                ),
                ("Task files: ", expected.get("task_files"), task_files_records),
                ("Task start: ", expected.get("start"), new_object.task_start.strftime(DATE_FORMAT)),
                ("Task finish: ", expected.get("finish"), new_object.deadline.strftime(DATE_FORMAT)),
                ("Task: ", expected.get("task"), new_object.task),
                ("Description: ", expected.get("description"), new_object.description),
                ("Tech_process: ", int(expected.get("tech_process")), new_object.tech_process),
                ("is_archived: ", int(expected.get("is_archived")), new_object.is_archived),
                (
                    "Duration: ",
                    (
                            datetime.strptime(expected["finish"], DATE_FORMAT)
                            - datetime.strptime(expected["start"], DATE_FORMAT)
                    ),
                    new_object.deadline - new_object.task_start
                ),
                ("user_id: ", expected.get("user_id"), new_object.user_id),
                ("executor_id: ", expected.get("executor_id"), new_object.executor_id),
            )
            for name_value, expected_value, exist_value in match_values:
                assert expected_value == exist_value, f"{name_value} {exist_value} not as expected: {expected_value}"
            if files_in_response is not None:
                for file in files_in_response:
                    assert file in all_files_in_folder, f"Can't find: {file} in files folder: {FILES_DIR}"
            await log.awarning(
                f"SCENARIO: _{scenario_number}_ info: {name}",
                files_attached_expected=expected.get("files_attached"),
                file_attached=set(file_names_attached),
                files_in_db=files_in_db,
                files_in_response=files_in_response,
                file_paths=file_paths,
                login_data=login,
                params=create_params,
                response=response.json(),
                task_files_records=task_files_records,
                task_files_expected=expected.get("task_files"),
                wings_of_end=f"_________ END of SCENARIO: ___ {scenario_number}___ {name}"
            )
            await clean_test_database(async_db, Task, FileAttached, TasksFiles)  # clean db after each single test
            await delete_files_in_folder(file_paths)
    await clean_test_database(async_db, User)


async def test_user_post_task_form_url(
        async_client: AsyncClient,
        async_db: AsyncSession,
        user_orm: User,
        user_from_settings: User,
) -> None:
    """
    Тестирует постановку задачи из формы с возможностью загрузки 1 файла:
    pytest -k test_user_post_task_form_url -vs

    scenarios - тестовые сценарии использования эндпоинта (все сценарии изолированы).
    expected - словарь ожидаемых значений в сценарии.
    match_values - кортеж параметров, используемых в assert (ожидание - реальность).
    """
    test_url = TASKS_PATH + POST_TASK_FORM  # /api/tasks/post_task_form
    user_orm_login = {"username": "user_fixture@f.com", "password": "testings"}
    user_from_settings_login = {"username": "user@example.com", "password": "testings"}
    now = datetime.now(TZINFO).strftime(DATE_FORMAT)
    day_ago = (datetime.now(TZINFO) - timedelta(days=1)).strftime(DATE_FORMAT)
    tomorrow = (datetime.now(TZINFO) + timedelta(days=1)).strftime(DATE_FORMAT)
    error_in_date = "11-07-20244"
    test_files = ["testfile.txt"]
    await create_test_files(test_files)
    file_to_upload = {"file_to_upload": open(TEST_ROUTES_DIR.joinpath(test_files[0]), "rb")}
    scenario_number = 0
    scenarios = (
        # login, params, status, file_to_upload, name
        (user_orm_login, {
            TASK_START: error_in_date,
            TASK_FINISH: day_ago,
            TASK: "1",
            TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
            TASK_DESCRIPTION: "error_in_date",
            TASK_EXECUTOR_MAIL: user_from_settings.email
            # TASK_EXECUTOR_MAIL_NOT_FROM_ENUM: None,
        }, 422, None, "error_in_date"),  # 1
        (user_orm_login, {
            TASK_START: now,
            TASK_FINISH: day_ago,
            TASK: "1",
            TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
            TASK_DESCRIPTION: "-1_[0]",
            TASK_EXECUTOR_MAIL: user_from_settings.email,
            # TASK_EXECUTOR_MAIL_NOT_FROM_ENUM: None,
        }, 422, None, "L > R: -1_[0] deadline < task start"),  # 2
        (user_orm_login, {
            TASK_START: now,
            TASK_FINISH: tomorrow,
            TASK: "1",
            TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
            TASK_DESCRIPTION: "[0]_+1",
            TASK_EXECUTOR_MAIL: user_from_settings.email,
            # TASK_EXECUTOR_MAIL_NOT_FROM_ENUM: None,
        }, 200, None, "tomorrow deadline"),  # 3
        (user_from_settings_login, {
            TASK_START: now,
            TASK_FINISH: tomorrow,
            TASK: "1",
            TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
            TASK_DESCRIPTION: "[0]_+1",
            TASK_EXECUTOR_MAIL: user_from_settings.email,
            # TASK_EXECUTOR_MAIL_NOT_FROM_ENUM: None,
        }, 200, None, "tomorrow deadline for myself task"),  # 4
        (user_orm_login, {
            TASK_START: now,
            TASK_FINISH: tomorrow,
            TASK: "1",
            TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
            TASK_DESCRIPTION: "[0]_+1",
            TASK_EXECUTOR_MAIL: user_from_settings.email,
            # TASK_EXECUTOR_MAIL_NOT_FROM_ENUM: None,
        }, 200, file_to_upload, "with file"),  # 5
        (user_orm_login, {
            TASK_START: now,
            TASK_FINISH: tomorrow,
            TASK: "1",
            TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
            TASK_DESCRIPTION: "[0]_+1",
            TASK_EXECUTOR_MAIL: user_from_settings.email,
            TASK_EXECUTOR_MAIL_NOT_FROM_ENUM: user_from_settings.email,
        }, 200, file_to_upload, "TASK_EXECUTOR_MAIL_NOT_FROM_ENUM BUT is ENUM"),  # 6
        (user_orm_login, {
            TASK_START: now,
            TASK_FINISH: tomorrow,
            TASK: "1",
            TECH_PROCESS: json.loads(settings.TECH_PROCESS)["DU_25"],
            TASK_DESCRIPTION: "[0]_+1",
            TASK_EXECUTOR_MAIL: user_from_settings.email,
            TASK_EXECUTOR_MAIL_NOT_FROM_ENUM: user_orm.email,
        }, 200, file_to_upload, "TASK_EXECUTOR_MAIL_NOT_FROM_ENUM == user_orm"),  # 7
    )
    async with async_client as ac:
        for login, create_params, status, files, name in scenarios:
            scenario_number += 1
            await log.ainfo(f"**************************************  SCENARIO: __ {scenario_number} __: {name}")
            response_login_user = await ac.post(LOGIN, data=login)
            response = await ac.post(
                test_url,
                params=create_params,
                headers={"Authorization": f"Bearer {response_login_user.json()['access_token']}"},
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
            objects = await async_db.scalars(select(Task))
            objects_in_db = objects.all()
            new_object = objects_in_db[0] if objects_in_db is not None else None
            total_objects = len(objects_in_db) if objects_in_db is not None else None
            # files attached:
            file_objects = await async_db.scalars(select(FileAttached))
            files_in_db = file_objects.all()
            files_in_response = response.json().get(FILES_SET_TO)
            all_files_in_folder = [file.name for file in FILES_DIR.glob('*')]
            file_paths = [
                FILES_DIR.joinpath(file_name) for file_name in files_in_response if files_in_response is not None
            ]
            # created files relations:
            task_files_object = await async_db.scalars(select(TasksFiles))
            task_files_in_db = task_files_object.all()
            task_files_records = set(
                ((record.task_id, record.file_id) for record in task_files_in_db)
            ) if files else None
            task_manager = await async_db.scalar(select(User).where(User.email == login.get("username")))
            if create_params.get(TASK_EXECUTOR_MAIL_NOT_FROM_ENUM) is not None:
                executor = await async_db.scalar(
                    select(User).where(User.email == create_params.get(TASK_EXECUTOR_MAIL_NOT_FROM_ENUM))
                )
            else:
                executor = await async_db.scalar(
                    select(User).where(User.email == create_params.get(TASK_EXECUTOR_MAIL))
                )
            expected = {  # expected values in scenario
                "total_objects_expected": 1,
                "task_expected_id": 1,  # could be response.json()["id"]
                "files_attached": test_files[0] if files else None,
                # "task_files": set(
                #     ((response.json()["id"], index[0] + 1) for index in enumerate(files_in_response))
                # ),  # actually is the same as in db, but smth else is needed todo
                "task_files": {(1, 1)} if files else None,  # just a plug - smth else is needed !!!
                "start": create_params.get(TASK_START),
                "finish": create_params.get(TASK_FINISH),
                "task": create_params.get(TASK),
                "description": create_params.get(TASK_DESCRIPTION),
                "tech_process": create_params.get(TECH_PROCESS),
                "is_archived": False,
                "user_id": task_manager.id,
                "executor_id": executor.id,
            }
            match_values = (
                # name_value, expected_value, exist_value
                ("Task id: ", expected.get("task_expected_id"), new_object.id),
                ("Total tasks: ", expected.get("total_objects_expected"), total_objects),
                (
                    "Attached files: ",
                    expected.get("files_attached"),
                    files_in_response[0].split("_")[-1] if len(files_in_response) > 0 else None,
                    # await get_file_names_for_model_db(async_db, Task, new_object.id),  # could be
                ),
                ("Task files: ", expected.get("task_files"), task_files_records),
                ("Task start: ", expected.get("start"), new_object.task_start.strftime(DATE_FORMAT)),
                ("Task finish: ", expected.get("finish"), new_object.deadline.strftime(DATE_FORMAT)),
                ("Task: ", expected.get("task"), new_object.task),
                ("Description: ", expected.get("description"), new_object.description),
                ("Tech_process: ", int(expected.get("tech_process")), new_object.tech_process),
                ("is_archived: ", int(expected.get("is_archived")), new_object.is_archived),
                (
                    "Duration: ",
                    (
                        datetime.strptime(expected["finish"], DATE_FORMAT)
                        - datetime.strptime(expected["start"], DATE_FORMAT)
                    ),
                    new_object.deadline - new_object.task_start
                ),
                ("user_id: ", expected.get("user_id"), new_object.user_id),
                ("executor_id: ", expected.get("executor_id"), new_object.executor_id),
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
                task_files_records=task_files_records,
                task_files_expected=expected.get("task_files"),
                wings_of_end=f"_________ END of SCENARIO: ___ {scenario_number}___ {name}"
            )
            await clean_test_database(async_db, Task, FileAttached, TasksFiles)  # clean db after each single test
            await delete_files_in_folder(file_paths)
    await clean_test_database(async_db, User)


async def test_user_get_task_url(
        async_client: AsyncClient,
        async_db: AsyncSession,
        tasks_orm: Task,
) -> None:
    """
    Тестирует возможность получения по id информации о задаче, или загрузки прикрепленных файлов:
    pytest -k test_user_get_task_url -vs

    before_patched - параметры задачи при ее создании: тождественны "scenarios" из tasks_orm в confest.py

    scenarios - тестовые сценарии использования эндпоинта (сценарии не изолированы друг от друга).
    expected - словарь ожидаемых значений в сценарии.
    match_values - кортеж параметров, используемых в assert (ожидание - реальность).

    """
    test_url = TASKS_PATH + "/"  # /api/tasks/{task_id}
    user_orm_login = {"username": "user_fixture@f.com", "password": "testings"}
    test_files = ["testfile.txt", "testfile2.txt", "testfile3.txt"]
    await create_test_files(test_files)
    file_to_attach = {"file_to_upload": open(TEST_ROUTES_DIR.joinpath(test_files[0]), "rb")}
    json_choice = [_ for _ in json.loads(settings.CHOICE_DOWNLOAD_FILES).values()][0]  # next(iter())
    files_choice = [_ for _ in json.loads(settings.CHOICE_DOWNLOAD_FILES).values()][1]  # 2nd == "files"
    scenario_number = 0
    scenarios = (
        # login, params, status, uploaded_file, task_id, name
        (user_orm_login, {CHOICE_FORMAT: json_choice}, 200, None, 1, "json-choice"),  # 1
        (user_orm_login, {CHOICE_FORMAT: json_choice}, 200, None, 2, "json-choice"),  # 2
        (user_orm_login, {CHOICE_FORMAT: files_choice}, 404, None, 2, "files_choice when no files attached"),  # 3
        (user_orm_login, {CHOICE_FORMAT: json_choice}, 200, file_to_attach, 3, "patch object by adding a file"),  # 4
        (user_orm_login, {CHOICE_FORMAT: json_choice}, 200, file_to_attach, 3, "adding one more file to object"),  # 5
        (user_orm_login, {CHOICE_FORMAT: json_choice}, 200, file_to_attach, 3, "adding one more file to object"),  # 5
        (user_orm_login, {CHOICE_FORMAT: json_choice}, 200, None, 3, "and now try to get attached files"),  # 6
        (user_orm_login, {CHOICE_FORMAT: files_choice}, 200, None, 3, "and now try to get attached files"),  # 7
        (user_orm_login, {CHOICE_FORMAT: json_choice}, 200, file_to_attach, 4, "and now try to get final json"),  # 8
    )
    async with async_client as ac:
        for login, params, status, uploaded_file, task_id, name in scenarios:
            scenario_number += 1
            await log.ainfo(f"**************************************  SCENARIO: __ {scenario_number} __: {name}")
            # grab info of objects in db before testing:
            objects_before = await async_db.scalars(select(Task))  # objects before scenarios have started
            objects_in_db_before = objects_before.all()  # objects before scenarios have started
            object_before_testing = [_ for _ in objects_in_db_before if _.id == task_id][0]
            attached_files_objects_before = await async_db.scalars(
                select(FileAttached)
                .join(Task.files)
                .where(Task.id == task_id)
            )
            attached_files_in_db_before = attached_files_objects_before.all()
            attached_files_paths_before = [
                FILES_DIR.joinpath(file.name) for file in attached_files_in_db_before
                if attached_files_in_db_before is not None
            ]
            task_files_object_before = await async_db.scalars(select(TasksFiles))
            task_files_in_db_before = task_files_object_before.all()
            task_files_records_before = set(
                ((record.task_id, record.file_id) for record in task_files_in_db_before)
            )
            task_manager = await async_db.scalar(select(User).where(User.id == object_before_testing.user_id))
            executor = await async_db.scalar(select(User).where(User.id == object_before_testing.executor_id))
            expected = {  # expected values in scenario
                "total_expected_before": len(objects_in_db_before),
                "task_id": task_id,
                "files_attached": [file.name for file in attached_files_in_db_before],
                "task_files": task_files_records_before,
                "task": object_before_testing.task,
                "start": object_before_testing.task_start,
                "duration": (
                        (object_before_testing.deadline - datetime.now().date()).total_seconds()
                        / TASK_DURATION_RESPONSE
                ),
                "finish": object_before_testing.deadline,
                "description": object_before_testing.description,
                "tech_process": int(object_before_testing.tech_process),
                "user_id": object_before_testing.user_id,
                "user_email": task_manager.email,
                "executor_email": executor.email,
                "executor_id": object_before_testing.executor_id,
                "is_archived": object_before_testing.is_archived,
            }
            response_login_user = await ac.post(LOGIN, data=login)
            if uploaded_file is not None:  # adding file to the object_id in order to get this file later
                response_patched = await ac.patch(
                    test_url + f"{task_id}",
                    params={TASK_DESCRIPTION: "task is attached with files"},
                    headers={"Authorization": f"Bearer {response_login_user.json()['access_token']}"},
                    files=uploaded_file
                )
                assert response_patched.status_code == status, (
                    f"User: {login} couldn't patch {test_url}. Response: {response.__dict__}"
                )
                file_attached_id = len(task_files_in_db_before) + 1  # fragile too much!
                expected["description"] = "task is attached with files"  # fragile !!!
                expected["files_attached"] = expected["files_attached"] + response_patched.json().get(FILES_SET_TO)
                expected["task_files"] = expected["task_files"].union(((task_id, file_attached_id),))
            response = await ac.get(
                test_url + f"{task_id}",
                params=params,
                headers={"Authorization": f"Bearer {response_login_user.json()['access_token']}"},
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
            # tasks after test running:
            objects = await async_db.scalars(select(Task))
            objects_in_db = objects.all()
            object_in_db = [_ for _ in objects_in_db if _.id == task_id][0]
            # files after test running:
            files_in_response = response.json().get(FILES_SET_TO)
            file_objects = await async_db.scalars(select(FileAttached))  # == [] when no files attached
            files_in_db = file_objects.all() if file_objects is not None else []
            file_paths = [
                FILES_DIR.joinpath(file_name) for file_name in files_in_response if files_in_response is not None
            ]
            all_files_in_folder = [file.name for file in FILES_DIR.glob('*')]
            # files relations after test running:
            task_files_object = await async_db.scalars(select(TasksFiles))
            task_files_in_db = task_files_object.all()
            task_files_records = set(
                ((record.task_id, record.file_id) for record in task_files_in_db)
            )
            # run asserts in a scenario:
            match_values = (
                # name_value, expected_value, exist_value
                ("Task id: ", expected.get("task_id"), object_before_testing.id),
                ("Total tasks: ", expected.get("total_expected_before"), len(objects_in_db)),
                ("Task: ", expected.get("task"), object_in_db.task),
                ("Attached files after: ", set(expected.get("files_attached")), set(files_in_response)),
                ("Task files: ", set(expected.get("task_files")), task_files_records),
                ("Task start: ", expected.get("start"), object_in_db.task_start),
                ("Task finish: ", expected.get("finish"), object_in_db.deadline),
                ("Description: ", expected.get("description"), object_in_db.description),
                (
                    "Tech process: ",
                    expected.get("tech_process"),
                    int(json.loads(settings.TECH_PROCESS).get(response.json().get(TECH_PROCESS)))
                ),
                ("Duration: ", expected.get("duration"), response.json().get(TASK_DURATION)),
                ("user_email: ", expected.get("user_email"), response.json().get(USER_MAIL)),
                ("user_id: ", expected.get("user_id"), object_in_db.user_id),
                ("executor_email: ", expected.get("executor_email"), response.json().get(TASK_EXECUTOR_MAIL)),
                ("executor_id: ", expected.get("executor_id"), object_in_db.executor_id),
                ("is_archived: ", expected.get("is_archived"), object_in_db.is_archived),
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
                task_files_expected=expected.get("task_files"),
                wings_of_end=f"______________ END of SCENARIO: ___ {scenario_number} ____ __{name} _______"
            )
    await delete_files_in_folder(file_paths)
    await clean_test_database(async_db, User, Task, FileAttached, TasksFiles)


async def test_user_get_all_tasks_url(
        async_client: AsyncClient,
        async_db: AsyncSession,
        tasks_orm: Task,
) -> None:
    """
    Тестирует возможность получения всех задач: pytest -k test_user_get_all_tasks_url -vs

    before_patched - параметры задачи при ее создании: тождественны "scenarios" из tasks_orm в confest.py

    scenarios - тестовые сценарии использования эндпоинта (сценарии не изолированы друг от друга).
    expected - словарь ожидаемых значений в сценарии.
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
            await log.ainfo(f"**************************************  SCENARIO: __ {scenario_number} __: {name}")
            response_login_user = await ac.post(LOGIN, data=login)
            response = await ac.get(
                test_url,
                headers={"Authorization": f"Bearer {response_login_user.json()['access_token']}"},
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
            for index in enumerate(tasks_orm):  # making checks of each object in tasks_orm and scenario response
                position = index[0] + 1  # task_id == 1
                fixture_object = [_ for _ in tasks_orm if _.id == position][0]
                object_in_response = [_ for _ in response.json() if _["id"] == position][0]
                # expected values in scenario - take original tasks_orm
                task_manager = await async_db.scalar(select(User).where(User.id == fixture_object.user_id))
                executor = await async_db.scalar(select(User).where(User.id == fixture_object.executor_id))
                expected = {  # expected values in scenario
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


async def test_user_get_all_tasks_opened_url(
        async_client: AsyncClient,
        async_db: AsyncSession,
        tasks_orm: Task,
) -> None:
    """
    Тестирует возможность получения всех открытых задач: pytest -k test_user_get_all_tasks_opened_url -vs

    before_patched - параметры задачи при ее создании: тождественны "scenarios" из tasks_orm в confest.py

    scenarios - тестовые сценарии использования эндпоинта (сценарии не изолированы друг от друга).
    expected - словарь ожидаемых значений в сценарии.
    match_values - кортеж параметров, используемых в assert (ожидание - реальность).

    """
    test_url = TASKS_PATH + GET_OPENED_ROUTE  # /api/tasks/opened
    user_orm_login = {"username": "user_fixture@f.com", "password": "testings"}
    scenario_number = 0
    scenarios = (
        # login, status, name, task_id
        (user_orm_login, 200, "all_tasks_are_opened", None),  # 1 all tasks are not archived
        (user_orm_login, 200, "task_id_1_is_archived", 1),  # 2 task_id = 1 is_archived
        (user_orm_login, 200, "task_id_2_is_archived", 2),  # 3 task_id = 2 is_archived
        (user_orm_login, 200, "task_id_3_is_archived", 3),  # 4 task_id = 3 is_archived
        (user_orm_login, 200, "task_id_4_is_archived", 4),  # 5 task_id = 4 is_archived
    )
    async with async_client as ac:
        for login, status, name, task_id in scenarios:
            scenario_number += 1
            await log.ainfo(f"**************************************  SCENARIO: __ {scenario_number} __: {name}")
            # making changes to tasks_orm:
            if task_id is not None:
                task = Task(id=task_id, description=f"task_id = {task_id} is_archived is true", is_archived=1)
                await async_db.merge(task)
                await async_db.commit()
            not_archived_objects = await async_db.scalars(select(Task).where(Task.is_archived == 0))
            tasks_opened = not_archived_objects.all()
            archived_objects = await async_db.scalars(select(Task).where(Task.is_archived == 1))
            tasks_closed = archived_objects.all()
            response_login_user = await ac.post(LOGIN, data=login)
            response = await ac.get(
                test_url,
                headers={"Authorization": f"Bearer {response_login_user.json()['access_token']}"},
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
            for task_opened in tasks_opened:  # making checks of each object in tasks_opened and response
                object_in_response = [_ for _ in response.json() if _["id"] == task_opened.id][0]
                # expected values in scenario - take original tasks_orm
                task_manager = await async_db.scalar(select(User).where(User.id == task_opened.user_id))
                executor = await async_db.scalar(select(User).where(User.id == task_opened.executor_id))
                expected = {  # expected values in scenario
                    "total_objects": len(tasks_opened),
                    "task_files": [],
                    "task": task_opened.task,
                    "start": task_opened.task_start.strftime(DATE_FORMAT),
                    "duration": (
                            (task_opened.deadline - datetime.now().date()).total_seconds() / TASK_DURATION_RESPONSE
                    ),
                    "finish": task_opened.deadline.strftime(DATE_FORMAT),
                    "description": task_opened.description,
                    "tech_process": int(task_opened.tech_process),
                    "user_id": task_opened.user_id,
                    "user_email": task_manager.email,
                    "executor_email": executor.email,
                    "executor_id": task_opened.executor_id,
                    "is_archived": task_opened.is_archived,
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
            for task_closed in tasks_closed:  # making checks of each object in tasks_closed and expectation
                expected_object = [task for task in tasks_orm if task.id == task_closed.id][0]
                # expected values in scenario - take original tasks_orm
                expected = {  # expected values in scenario
                    "total_objects": scenario_number - 1,
                    "task": expected_object.task,
                    "start": expected_object.task_start.strftime(DATE_FORMAT),
                    "finish": expected_object.deadline.strftime(DATE_FORMAT),
                    "description": f"task_id = {task_closed.id} is_archived is true",
                    "tech_process": int(expected_object.tech_process),
                    "user_id": expected_object.user_id,
                    "executor_id": expected_object.executor_id,
                    "is_archived": 1,
                }
                # run asserts in a scenario:
                match_values = (
                    # name_value, expected_value, exist_value
                    ("Total tasks: ", expected.get("total_objects"), len(tasks_closed)),
                    ("Task: ", expected.get("task"), task_closed.task),
                    ("Task start: ", expected.get("start"), task_closed.task_start.strftime(DATE_FORMAT)),
                    ("Task finish: ", expected.get("finish"), task_closed.deadline.strftime(DATE_FORMAT)),
                    ("Description: ", expected.get("description"), task_closed.description),
                    ("Tech process: ", expected.get("tech_process"), int(task_closed.tech_process)),
                    ("user_id: ", expected.get("user_id"), task_closed.user_id),
                    ("executor_id: ", expected.get("executor_id"), task_closed.executor_id),
                    ("is_archived: ", expected.get("is_archived"), task_closed.is_archived),
                )
                for name_value, expected_value, exist_value in match_values:
                    assert expected_value == exist_value, (
                        f"{name_value} {exist_value} not as expected: {expected_value}"
                    )
            await log.ainfo(
                f"SCENARIO: _{scenario_number}_ info: {name}",
                tasks_opened=tasks_opened,
                tasks_closed=tasks_closed,
                login_data=login,
                response=response.json(),
                wings_of_end=f"______________ END of SCENARIO: ___ {scenario_number} ____ __{name} _______"
            )
    await clean_test_database(async_db, User, Task, FileAttached, TasksFiles)


async def test_user_get_my_tasks_ordered_url(
        async_client: AsyncClient,
        async_db: AsyncSession,
        tasks_orm: Task,
) -> None:
    """
    Тестирует получение задач, выставленных пользователем: pytest -k test_user_get_my_tasks_ordered_url -vs

    before_patched - параметры задачи при ее создании: тождественны "scenarios" из tasks_orm в confest.py

    scenarios - тестовые сценарии использования эндпоинта (сценарии не изолированы друг от друга).
    expected - словарь ожидаемых значений в сценарии.
    match_values - кортеж параметров, используемых в assert (ожидание - реальность).

    """
    test_url = TASKS_PATH + MY_TASKS  # /api/tasks/my_tasks_ordered
    user_orm_login = {"username": "user_fixture@f.com", "password": "testings"}
    user_from_settings_login = {"username": "user@example.com", "password": "testings"}
    scenario_number = 0
    scenarios = (
        # login, status, name
        (user_orm_login, 200, "get_all_user_orm_tasks_ordered"),  # 1
        (user_from_settings_login, 200, "get_all_user_from_settings_tasks_ordered"),  # 1
    )
    async with async_client as ac:
        for login, status, name in scenarios:
            scenario_number += 1
            await log.ainfo(f"**************************************  SCENARIO: __ {scenario_number} __: {name}")
            response_login_user = await ac.post(LOGIN, data=login)
            response = await ac.get(
                test_url,
                headers={"Authorization": f"Bearer {response_login_user.json()['access_token']}"},
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
            task_manager = await async_db.scalar(select(User).where(User.email == login.get("username")))
            fixture_objects_expected = [_ for _ in tasks_orm if _.user_id == task_manager.id]
            for object_in_response in response.json():
                fixture_object = [_ for _ in fixture_objects_expected if _.id == object_in_response["id"]][0]
                executor = await async_db.scalar(select(User).where(User.id == fixture_object.executor_id))
                expected = {  # expected values in scenario
                    "total_objects": len(fixture_objects_expected),
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


async def test_super_user_add_files_to_task_url(
        async_client: AsyncClient,
        async_db: AsyncSession,
        tasks_orm: Task,
        super_user_orm: User
) -> None:
    """
    Тестирует добавление супер-пользователем к задаче id файлов из формы:
    pytest -k test_super_user_add_files_to_task_url -vs

    before_patched - параметры задачи при ее создании: тождественны "scenarios" из tasks_orm в confest.py

    scenarios - тестовые сценарии использования эндпоинта (сценарии не изолированы друг от друга).
    expected - словарь ожидаемых значений в сценарии.
    match_values - кортеж параметров, используемых в assert (ожидание - реальность).

    """
    test_url = TASKS_PATH + ADD_FILES_TO_TASK  # /api/tasks/add_files_to_task
    download_files_url = FILES_PATH + DOWNLOAD_FILES  # /api/files/download_files
    user_orm_login = {"username": "user_fixture@f.com", "password": "testings"}
    super_user_login = {"username": super_user_orm.email, "password": "testings"}
    test_files = ["testfile.txt", "testfile2.txt", "testfile3.txt"]
    await create_test_files(test_files)
    files_to_delete_at_the_end = []
    scenario_number = 0
    scenarios = (
        # login, params, status, file_index, name - Dependant scenarios !!!
        (user_orm_login, {'task_id': 1, SET_FILES_LIST_TO_TASK: [1]}, 403, 0, "obj_1 not admin"),  # 1
        (super_user_login, {'task_id': 1, SET_FILES_LIST_TO_TASK: [1]}, 200, 0, "obj_1 add file_id 1"),  # 2
        (super_user_login, {'task_id': 1, SET_FILES_LIST_TO_TASK: [2]}, 200, 1, "obj_1 add f_id 2"),  # 3
        (super_user_login, {'task_id': 1, SET_FILES_LIST_TO_TASK: [1, 2]}, 200, 2, "obj_1 fls: 1,2"),  # 4
        (super_user_login, {'task_id': 2, SET_FILES_LIST_TO_TASK: [1, 2, 3]}, 200, 2, "obj_2 fls: 1,2,3"),
        (super_user_login, {'task_id': 3, SET_FILES_LIST_TO_TASK: [1, 2, 3, 4, 5]}, 200, 2, "obj_3 5 fls"),
    )
    async with async_client as ac:
        for login, create_params, status, file_index, name in scenarios:
            scenario_number += 1
            await log.ainfo(f"**************************************  SCENARIO: __ {scenario_number} __: {name}")
            # grab objects in db info before testing:
            task_id = create_params.get('task_id')
            task_files_object_before = await async_db.scalars(select(TasksFiles))
            task_files_in_db_before = task_files_object_before.all()
            object_id_task_files_before = await async_db.scalars(
                select(TasksFiles)
                .where(TasksFiles.task_id == task_id)
            )
            object_id_task_files_before_all = object_id_task_files_before.all()  # task_files attached to the object_id
            response_login_super_user = await ac.post(LOGIN, data=super_user_login)  # only super_user is allowed!
            assert response_login_super_user.status_code == 200, f"Super_user: {super_user_login} can't get {LOGIN}"
            # downloading files with api to test it in scenarios
            download_files_response = await ac.post(
                download_files_url,
                files={"files": open(TEST_ROUTES_DIR.joinpath(test_files[file_index]), "rb")},
                headers={"Authorization": f"Bearer {response_login_super_user.json()['access_token']}"},
            )
            assert download_files_response.status_code == 200, (
                f"User: {super_user_login} can't get {download_files_url} Response: {download_files_response.__dict__}"
            )
            file_objects = await async_db.scalars(select(FileAttached))
            files_in_db = file_objects.all()
            files_downloaded_response = download_files_response.json().get(FILES_WRITTEN_DB)
            file_names_added = [file_dict.get("Имя файла.") for file_dict in files_downloaded_response]
            file_paths = [
                FILES_DIR.joinpath(file_name) for file_name in file_names_added if file_names_added is not None
            ]
            response_login_user = await ac.post(LOGIN, data=login)  # files are attached, so tests could be started
            response = await ac.post(
                test_url,
                params=create_params,
                headers={"Authorization": f"Bearer {response_login_user.json()['access_token']}"},
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
            # patched tasks:
            objects = await async_db.scalars(select(Task))
            objects_in_db = objects.all()
            object_in_db = [_ for _ in objects_in_db if _.id == task_id][0]
            # patched files:
            attached_files_objects = await async_db.scalars(
                select(FileAttached)
                .join(Task.files)
                .where(Task.id == task_id)
            )
            attached_files_in_db = attached_files_objects.all()
            file_names_attached = [file.name for file in attached_files_in_db]
            all_files_in_folder = [file.name for file in FILES_DIR.glob('*')]
            files_by_ids_in_db = await async_db.scalars(
                select(FileAttached).where(FileAttached.id.in_(create_params.get(SET_FILES_LIST_TO_TASK)))
            )
            files_by_ids_in_db_all = files_by_ids_in_db.all()
            file_names_get_by_set_ids = [file.name for file in files_by_ids_in_db_all]
            file_objects = await async_db.scalars(select(FileAttached))  # == [] when no files attached
            files_in_db = file_objects.all() if file_objects is not None else []
            files_to_delete_at_the_end += file_paths
            # task_files:
            task_files_object = await async_db.scalars(select(TasksFiles))
            task_files_in_db = task_files_object.all()
            task_files_expected = set(task_files_in_db_before).difference(set(object_id_task_files_before_all))
            task_files_expected = list(task_files_expected)
            for file_id in create_params.get(SET_FILES_LIST_TO_TASK):
                task_files_expected.append(f'<Task {task_id} - Files {file_id}>')
            # run asserts in a scenario:
            expected = {  # expected values in scenario
                "files_attached": file_names_get_by_set_ids,
                "task_files": [str(record) for record in task_files_expected],
            }
            match_values = (
                # name_value, expected_value, exist_value
                ("Task id: ", task_id, object_in_db.id),
                ("Attached files: ", set(expected.get("files_attached")), set(file_names_attached)),
                ("Task files: ", set(expected.get("task_files")), set([str(record) for record in task_files_in_db])),
            )
            for name_value, expected_value, exist_value in match_values:
                assert expected_value == exist_value, f"{name_value} {exist_value} not as expected: {expected_value}"
            if file_names_added is not None:
                for file in file_names_added:
                    assert file in all_files_in_folder, f"Can't find: {file} in files folder: {FILES_DIR}"
            await log.ainfo(
                f"SCENARIO: _{scenario_number}_ info: {name}",
                all_files_in_db=files_in_db,
                file_names_attached_to_task=file_names_attached,
                file_names_downloaded=file_names_added,
                file_names_get_by_set_ids=file_names_get_by_set_ids,
                login_data=login,
                params=create_params,
                response=response.json(),
                task_files_in_db_before=task_files_in_db_before,
                task_files_in_db=task_files_in_db,
                wings_of_end=f"_______________________________________________ END of SCENARIO: ___ {scenario_number}"
            )
    await clean_test_database(async_db, User, Task, FileAttached, TasksFiles)
    await delete_files_in_folder(files_to_delete_at_the_end)


async def test_super_user_delete_task_url(
        async_client: AsyncClient,
        async_db: AsyncSession,
        tasks_orm: Task,
        super_user_orm: User
) -> None:
    """
    Тестирует удаление супер-пользователем задачи по id из формы:
    pytest -k test_super_user_delete_task_url -vs

    before_patched - параметры задачи при ее создании: тождественны "scenarios" из suspensions_orm в confest.py

    scenarios - тестовые сценарии использования эндпоинта (сценарии не изолированы друг от друга).
    expected - словарь ожидаемых значений в сценарии.
    match_values - кортеж параметров, используемых в assert (ожидание - реальность).

    """
    test_url = TASKS_PATH + "/"  # /api/tasks/{task_id}
    download_files_url = FILES_PATH + DOWNLOAD_FILES  # /api/files/download_files
    user_orm_login = {"username": "user_fixture@f.com", "password": "testings"}
    super_user_login = {"username": super_user_orm.email, "password": "testings"}
    test_files = ["testfile.txt", "testfile2.txt", "testfile3.txt"]
    files_list_set_to_task = [1]
    await create_test_files(test_files)
    scenario_number = 0
    files_to_delete_at_the_end = []
    scenarios = (
        # login, params, status, file_index, name, add_file_to_suspension_id
        (user_orm_login, {'task_id': 1}, 403, 0, "obj_1 not admin", 1),  # 1
        (super_user_login, {'task_id': 1}, 200, 0, "delete obj_1", 1),  # 2
        (super_user_login, {'task_id': 1}, 404, 0, "can't delete obj_1 again", 2),  # 3
        (super_user_login, {'task_id': 2}, 200, 0, "delete obj_2 with 2 files", 2),  # 4
    )
    async with async_client as ac:
        for login, create_params, status, file_index, name, add_file_to_task_id in scenarios:
            scenario_number += 1
            await log.ainfo(f"**************************************  SCENARIO: __ {scenario_number} __: {name}")
            # grab objects in db info before testing:
            task_id = create_params.get('task_id')
            task_files_object_before = await async_db.scalars(select(TasksFiles))
            task_files_in_db_before = task_files_object_before.all()
            response_login_super_user = await ac.post(LOGIN, data=super_user_login)  # only super_user is allowed!
            assert response_login_super_user.status_code == 200, f"Super_user: {super_user_login} can't get {LOGIN}"
            # DOWNLOAD files with api to test removing files along with task
            download_files_response = await ac.post(
                download_files_url,
                files={"files": open(TEST_ROUTES_DIR.joinpath(test_files[file_index]), "rb")},
                headers={"Authorization": f"Bearer {response_login_super_user.json()['access_token']}"},
            )
            assert download_files_response.status_code == 200, (
                f"User: {super_user_login} can't get {download_files_url} Response: {download_files_response.__dict__}"
            )
            set_files_response = await ac.post(
                TASKS_PATH + ADD_FILES_TO_TASK,
                params={
                    'task_id': add_file_to_task_id,
                    SET_FILES_LIST_TO_TASK: files_list_set_to_task
                },
                headers={"Authorization": f"Bearer {response_login_super_user.json()['access_token']}"},
            )
            assert set_files_response.status_code == 200, (
                f"User: {login} can't get {test_url}. Response: {set_files_response.__dict__}"
            )
            files_in_response = download_files_response.json().get(FILES_WRITTEN_DB)
            file_names_added = [file_dict.get("Имя файла.") for file_dict in files_in_response]
            all_files_in_folder = [file.name for file in FILES_DIR.glob('*')]
            if file_names_added is not None:
                for file in file_names_added:
                    assert file in all_files_in_folder, f"Can't find: {file} in files folder: {FILES_DIR}"
            # START TESTINGS WITH FILES ATTACHED!
            objects = await async_db.scalars(select(Task))
            objects_in_db_before = objects.all()
            object_in_db_before = [_ for _ in objects_in_db_before if _.id == task_id]
            # attached files:
            attached_files_objects = await async_db.scalars(
                select(FileAttached)
                .join(Task.files)
                .where(Task.id == task_id)
            )
            attached_files_in_db = attached_files_objects.all()
            file_paths = [
                FILES_DIR.joinpath(file_name) for file_name in file_names_added if file_names_added is not None
            ]
            files_to_delete_at_the_end += file_paths  # unified solution
            response_login_user = await ac.post(LOGIN, data=login)
            response = await ac.delete(
                test_url + f"{task_id}",
                params=create_params,
                headers={"Authorization": f"Bearer {response_login_user.json()['access_token']}"},
            )
            assert response.status_code == status, f"User: {login} can't get {test_url}. Response: {response.__dict__}"
            if response.status_code != 200:
                await log.ainfo(
                    f"SCENARIO: ___ status_code != 200___ _{scenario_number}_ info: {name}",
                    attached_files_in_db=attached_files_in_db,
                    login_data=login,
                    params=create_params,
                    response=response.json(),
                    status=response.status_code,
                    wings_of_end=f"STATUS: {response.status_code}___ END of SCENARIO: ___ {scenario_number}  _{name}_"
                )
                await delete_files_in_folder(file_paths)
                await clean_test_database(async_db, FileAttached, TasksFiles)  # clean data after failed scenario
                continue
            # run asserts in a scenario:
            # grab objects in db info after testing:
            objects = await async_db.scalars(select(Task))
            objects_in_db = objects.all()
            object_in_db = [_ for _ in objects_in_db if _.id == task_id]
            attached_files_objects = await async_db.scalars(
                select(FileAttached)
                .join(Task.files)
                .where(Task.id == task_id)
            )
            attached_files_in_db = attached_files_objects.all()
            # patched files relations:
            task_files_object_after = await async_db.scalars(select(TasksFiles))
            task_files_in_db_after = task_files_object_after.all()
            all_files_in_folder = [file.name for file in FILES_DIR.glob('*')]
            if file_names_added is not None:
                for file in file_names_added:
                    assert file not in all_files_in_folder, f"{file} in files folder: {FILES_DIR}, but shouldn't"
            expected = {  # expected values in scenario
                "tasks_after": len(objects_in_db_before) - 1,
                "task_id_in_db": [],
                "file_in_db": [],
            }
            match_values = (
                # name_value, expected_value, exist_value
                ("Task id: ", task_id, object_in_db_before[0].id),
                ("Total tasks after: ", expected.get("tasks_after"), len(objects_in_db)),
                ("No object in db: ", expected.get("task_id_in_db"), object_in_db),
                ("No file attached in db: ", expected.get("file_in_db"), attached_files_in_db),
                ("No file relations in db: ", task_files_in_db_before, task_files_in_db_after),
            )
            for name_value, expected_value, exist_value in match_values:
                assert expected_value == exist_value, f"{name_value} {exist_value} not as expected: {expected_value}"
            await log.ainfo(
                f"SCENARIO: _{scenario_number}_ info: {name}",
                files_in_db_after=attached_files_in_db,
                file_names_added=file_names_added,
                objects_in_db_before=objects_in_db_before,
                objects_in_db=objects_in_db,
                login_data=login,
                params=create_params,
                response=response.json(),
                task_files_in_db_after=task_files_in_db_after,
                task_files_in_db_before=task_files_in_db_before,
                wings_of_end=f"_______________________________________________ END of SCENARIO: ___ {scenario_number}"
            )
    await clean_test_database(async_db, User, Task, FileAttached, TasksFiles)
    await delete_files_in_folder(files_to_delete_at_the_end)
