"""
Асинхронные тесты работы эндпоинтов работы с файлами: tests/test_routes/test_attached_files.py
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

from tests.conftest import delete_files_in_folder, get_file_names_for_model_db, remove_all


log = structlog.get_logger() if settings.FILE_NAME_IN_LOG is False else structlog.get_logger().bind(file_name=__file__)
pytestmark = pytest.mark.anyio  # make all test mark with `anyio` or use decorator: # @pytest.mark.anyio

FILES_PATH = settings.ROOT_PATH + "/files"  # /api/files/  # todo удалить / перенести

SERVICES_DIR = Path(__file__).resolve().parent.parent.parent
FILES_DIR = SERVICES_DIR.joinpath(settings.FILES_DOWNLOAD_DIR)
TEST_ROUTES_DIR = Path(__file__).resolve().parent  # todo

# TODO endpoints files
# ADD_FILES_TO_SUSPENSION = "/add_files_to_suspension"
# # ANALYTICS = "/analytics"  # is done!
# MY_SUSPENSIONS = "/my_suspensions"
# # POST_SUSPENSION_FORM = "/post_suspension_form"  # todo now
# POST_SUSPENSION_FILES_FORM = "/post_suspension_with_files_form"
# SUSPENSION_ID = "/{suspension_id}"


# async def test_unauthorized_tries_files_urls(async_client: AsyncClient) -> None:  # TODO
#     """
#     Тестирует доступ к эндпоинтам работы с файлами неавторизованным пользователем:
#     pytest -k test_unauthorized_tries_suspension_urls -vs
#     """
#     # print(f"suspension_router: {suspension_router.routes}")
#     get_params_urls = (
#         (SUSPENSIONS_PATH+ANALYTICS, {}, 401),  # /api/suspensions/analytics
#         (SUSPENSIONS_PATH + MAIN_ROUTE, {}, 401),  # /api/suspensions/
#         (SUSPENSIONS_PATH + MY_SUSPENSIONS, {}, 401),  # /api/my_suspensions/
#         (SUSPENSIONS_PATH + SUSPENSION_ID, {}, 401),  # /api/suspensions/{suspension_id}
#     )
#     patch_data_urls = (
#         (SUSPENSIONS_PATH+SUSPENSION_ID, {}, 401),  # /api/suspensions/{suspension_id}
#     )
#     post_data_urls = (
#         (SUSPENSIONS_PATH+POST_SUSPENSION_FORM, {}, 401),  # /api/suspensions/post_suspension_form
#         (SUSPENSIONS_PATH + POST_SUSPENSION_FILES_FORM, {}, 401),  # /api/suspensions/post_suspension_with_files_form
#         (SUSPENSIONS_PATH + ADD_FILES_TO_SUSPENSION, {}, 401),  # /api/suspensions/add_files_to_suspension
#     )
#
#     async with async_client as ac:
#         for api_url, params, status in get_params_urls:
#             response = await ac.get(api_url, params=params)
#             assert response.status_code == status, f"test_url: {api_url} with params: {params} is not {status}"
#             await log.ainfo(
#                 "{}".format(api_url), response=response.json(), status=response.status_code, request=response._request
#             )
#         for api_url, data, status in patch_data_urls:
#             response = await ac.patch(api_url, data=data)
#             assert response.status_code == status, f"test_url: {api_url} with data: {data} is not {status}"
#             await log.ainfo(
#                 "{}".format(api_url), data=data, response=response.json(), status=response.status_code,
#                 request=response._request,
#             )
#         for api_url, data, status in post_data_urls:
#             response = await ac.post(api_url, data=data)
#             assert response.status_code == status, f"test_url: {api_url} with data: {data} is not {status}"
#             await log.ainfo(
#                 "{}".format(api_url), data=data, response=response.json(), status=response.status_code,
#                 request=response._request,
#             )
#             # print(f'response: {dir(response)}')

# TODO finish!!!
# - имя файла совпадает с ожиданиями todo
# - файл записался в БД todo
# - файл сохранился в каталоге файлов todo
# - появилась запись в таблице SuspensionsFiles todo
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
            files={"files": open(TEST_ROUTES_DIR.joinpath("testfile.txt"), "rb")},
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