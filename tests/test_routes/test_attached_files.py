"""
Асинхронные тесты работы эндпоинтов работы с файлами: tests/test_routes/test_attached_files.py
pytest -s -W ignore::DeprecationWarning
pytest -k test_unauthorized_get_urls -vs
pytest -k test_attached_files.py -vs  # тесты только из этого файла
pytest -vs  # все тесты
https://anyio.readthedocs.io/en/stable/testing.html

pytest -k test_unauthorized_tries_file_urls -vs
pytest -k test_user_post_download_files_url -vs
pytest -k test_user_get_files_url -vs  #
pytest -k test_user_get_file_id_url -vs  # todo

pytest -k test_super_user_delete_file_id_url -vs  # todo
pytest -k test_super_user_delete_files_unused_url -vs  # todo - самый сложный !!!


Для отладки рекомендуется использовать:
print(f'response_dir: {dir(response)}')
print(f'RESPONSE__dict__: {response.__dict__}')
"""
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
from src.core.db.models import FileAttached, User
from src.settings import settings

from tests.conftest import clean_test_database, create_test_files, delete_files_in_folder, remove_all


log = structlog.get_logger() if settings.FILE_NAME_IN_LOG is False else structlog.get_logger().bind(file_name=__file__)
pytestmark = pytest.mark.anyio  # make all test mark with `anyio` or use decorator: # @pytest.mark.anyio

FILES_PATH = settings.ROOT_PATH + "/files"  # /api/files/

SERVICES_DIR = Path(__file__).resolve().parent.parent.parent
FILES_DIR = SERVICES_DIR.joinpath(settings.FILES_DOWNLOAD_DIR)
TEST_ROUTES_DIR = Path(__file__).resolve().parent


async def test_unauthorized_tries_file_urls(async_client: AsyncClient) -> None:
    """
    Тестирует доступ к эндпоинтам работы с файлами неавторизованным пользователем:
    pytest -k test_unauthorized_tries_file_urls -vs
    """
    get_params_urls = (
        (FILES_PATH + GET_FILES, {}, 401),  # /api/files/get_files
        (FILES_PATH + FILE_ID, {}, 401),  # /api/files/{file_id}
    )
    delete_params_urls = (
        (FILES_PATH + FILE_ID, {}, 401),  # /api/files/{file_id}
        (FILES_PATH + GET_FILES_UNUSED, {}, 401),  # /api/files//get_files_unused
    )
    post_data_urls = (
        (FILES_PATH + DOWNLOAD_FILES, {}, 401),  # /api/files/download_files
    )

    async with async_client as ac:
        for api_url, params, status in get_params_urls:
            response = await ac.get(api_url, params=params)
            assert response.status_code == status, f"test_url: {api_url} with params: {params} is not {status}"
            await log.ainfo(
                "{}".format(api_url), response=response.json(), status=response.status_code, request=response._request
            )
        for api_url, params, status in delete_params_urls:
            response = await ac.delete(api_url, params=params)
            assert response.status_code == status, f"test_url: {api_url} with params: {params} is not {status}"
            await log.ainfo(
                "{}".format(api_url), response=response.json(), status=response.status_code, request=response._request
            )
        for api_url, data, status in post_data_urls:
            response = await ac.post(api_url, data=data)
            assert response.status_code == status, f"test_url: {api_url} with data: {data} is not {status}"
            await log.ainfo(
                "{}".format(api_url), data=data, response=response.json(), status=response.status_code,
                request=response._request,
            )


async def test_user_post_download_files_url(
        async_client: AsyncClient,
        async_db: AsyncSession,
        user_orm: User,
        super_user_orm: User,
) -> None:
    """
    Тестирует возможность загрузки 1 файла:
    pytest -k test_user_post_download_files_url -vs

    scenarios - тестовые сценарии использования эндпоинта (все сценарии изолированы).
    expected - словарь ожидаемых значений в сценарии.
    match_values - кортеж параметров, используемых в assert (ожидание - реальность).
    """
    test_url = FILES_PATH + DOWNLOAD_FILES  # /api/files/download_files
    super_user_login = {"username": super_user_orm.email, "password": "testings"}
    user_orm_login = {"username": "user_fixture@f.com", "password": "testings"}
    test_files = ["testfile.txt", "testfile2.txt", "testfile3.txt"]
    await create_test_files(test_files)
    files = (
        ("files", open(TEST_ROUTES_DIR.joinpath(test_files[0]), "rb")),
        ("files", open(TEST_ROUTES_DIR.joinpath(test_files[1]), "rb")),
        ("files", open(TEST_ROUTES_DIR.joinpath(test_files[2]), "rb"))
    )
    scenario_number = 0
    scenarios = (
        # login, status, files, test_files, name
        (super_user_login, 200, files, test_files, "success downloading 3 files scenario"),  # 1
        (user_orm_login, 403, files, test_files, "not admin is forbidden to download files"),  # 2
        (
            super_user_login,
            200,
            (("files", open(TEST_ROUTES_DIR.joinpath(test_files[0]), "rb")),),
            ("testfile.txt",),
            "just 1 file to download"
        ),  # 3
        (super_user_login, 400, (("files", None),), (None, ), "None file to download"),  # 4
    )
    async with async_client as ac:
        # !!!! starting testing scenarios:
        for login, status, files, test_files, name in scenarios:
            scenario_number += 1
            await log.ainfo(f"**************************************  SCENARIO: __ {scenario_number} __: {name}")
            login_user_response = await ac.post(LOGIN, data=login)
            assert login_user_response.status_code == 200, f"User: {login} couldn't get {LOGIN}"
            response = await ac.post(
                test_url,
                headers={"Authorization": f"Bearer {login_user_response.json()['access_token']}"},
                files=files
            )
            assert response.status_code == status, f"{login} couldn't get {test_url}. Response: {response.__dict__}"
            if response.status_code != 200:
                await log.ainfo(
                    f"SCENARIO: _{scenario_number}_ info: ",
                    login_data=login,
                    response=response.json(),
                    status=response.status_code,
                    wings_of_end=f"STATUS: {response.status_code}___ END of SCENARIO: ___ {scenario_number} ___ {name}"
                )
                continue
            # files downloaded:
            file_objects = await async_db.scalars(select(FileAttached))
            files_in_db = file_objects.all()
            file_names_in_db = [file.name.split("_")[-1] for file in files_in_db if len(files_in_db) > 0]
            files_in_response = [_.get(FILE_NAME) for _ in response.json().get(FILES_WRITTEN_DB)]
            file_names_in_response = [file.split("_")[-1] for file in files_in_response if len(files_in_response) > 0]
            all_files_in_folder = [file.name for file in FILES_DIR.glob('*')]
            if files_in_response is not None:
                for file in files_in_response:
                    assert file in all_files_in_folder, f"Can't find: {file} in files folder: {FILES_DIR}"
            file_paths = [
                FILES_DIR.joinpath(file_name) for file_name in files_in_response if files_in_response is not None
            ]
            expected = {  # expected values in scenario
                "total_files_in_db": len(files),
                "files_downloaded": set(test_files) if files else None,
            }
            match_values = (
                # name_value, expected_value, exist_value
                ("Files in db total: ", expected.get("total_files_in_db"), len(files_in_db)),
                ("Downloaded files in response: ", expected.get("files_downloaded"), set(file_names_in_response)),
                ("Downloaded files in db: ", expected.get("files_downloaded"), set(file_names_in_db)),
            )
            for name_value, expected_value, exist_value in match_values:
                assert expected_value == exist_value, f"{name_value} {exist_value} not as expected: {expected_value}"
            await log.awarning(
                f"SCENARIO: _{scenario_number}_ info: {name}",
                files_downloaded=set(test_files) if files else None,
                files_in_db=files_in_db,
                files_in_response=files_in_response,
                login_data=login,
                wings_of_end=f"_________ END of SCENARIO: ___ {scenario_number}___ {name}"
            )
            await clean_test_database(async_db, FileAttached)  # clean db after each single test
            await delete_files_in_folder(file_paths)
    all_files_in_folder = [file.name for file in FILES_DIR.glob('*')]  # todo добавить проверку во все тесты с файлами
    if files_in_response is not None:
        for file in files_in_response:
            assert file not in all_files_in_folder, f"{file} in files folder: {FILES_DIR}, but shouldn't"
    await clean_test_database(async_db, User)


async def test_user_get_files_url(
        async_client: AsyncClient,
        async_db: AsyncSession,
        user_orm: User,
        super_user_orm: User,
) -> None:
    """
    Тестирует возможность получения нескольких файлов по запросу по ключевому слову:
    pytest -k test_user_get_files_url -vs

    scenarios - тестовые сценарии использования эндпоинта (все сценарии изолированы).
    expected - словарь ожидаемых значений в сценарии.
    match_values - кортеж параметров, используемых в assert (ожидание - реальность).
    """
    test_url = FILES_PATH + GET_FILES  # /api/files/get_files
    download_files_url = FILES_PATH + DOWNLOAD_FILES  # /api/files/download_files
    super_user_login = {"username": super_user_orm.email, "password": "testings"}
    user_orm_login = {"username": "user_fixture@f.com", "password": "testings"}
    test_files = ["testfile.txt", "testfile2.txt", "testfile3.txt"]
    now = datetime.now(TZINFO).strftime(DATE_FORMAT)
    await create_test_files(test_files)
    files = (
        ("files", open(TEST_ROUTES_DIR.joinpath(test_files[0]), "rb")),
        ("files", open(TEST_ROUTES_DIR.joinpath(test_files[1]), "rb")),
        ("files", open(TEST_ROUTES_DIR.joinpath(test_files[2]), "rb"))
    )
    scenario_number = 0
    scenarios = (
        # params, status, expected_key, name
        ({}, 404, "all_db_files", "empty search by file_name"),  # 1
        ({SEARCH_FILES_BY_ID: []}, 404, "no_files", "empty search by file_ids == []"),  # 2
        ({SEARCH_FILES_BY_NAME: "???", SEARCH_FILES_BY_ID: [1]}, 403, "no_files", "by name & ids simultaneously"),  # 3
        ({SEARCH_FILES_BY_NAME: "no exist"}, 404, "no_files", "search files by name no exist"),  # 4
        ({SEARCH_FILES_BY_NAME: "testfile"}, 200, "all_db_files", "search 3 files by part name"),  # 5
        ({SEARCH_FILES_BY_NAME: "testfile3"}, 200, "testfile3", "search 1 file by part name"),  # 6
        ({SEARCH_FILES_BY_NAME: f"{now}"}, 200, "all_db_files", "search files by date"),  # 7
        ({SEARCH_FILES_BY_ID: [3]}, 200, "testfile3", "search files by id == 3"),  # 8
        ({SEARCH_FILES_BY_ID: [3, 2]}, 200, "testfiles_3_2", "search files by id == 1, 2"),  # 9
        ({SEARCH_FILES_BY_ID: [3, 55]}, 200, "testfile3", "search files by id == 1, 55"),  # 10
        ({SEARCH_FILES_BY_ID: [55]}, 200, "no_files", "search files by id == 55 no exists"),  # 11
    )
    async with async_client as ac:
        login_super_user_response = await ac.post(LOGIN, data=super_user_login)
        assert login_super_user_response.status_code == 200, f"User: {super_user_login} couldn't get {LOGIN}"
        uploaded_files_response = await ac.post(
            download_files_url,
            headers={"Authorization": f"Bearer {login_super_user_response.json()['access_token']}"},
            files=files
        )
        assert uploaded_files_response.status_code == 200, (
            f"{user_orm_login} couldn't get {uploaded_files_response}. Response: {uploaded_files_response.__dict__}"
        )
        # files downloaded:
        file_objects = await async_db.scalars(select(FileAttached))
        file_objects_in_db = file_objects.all()
        files_in_db = [file.name for file in file_objects_in_db if len(file_objects_in_db) > 0]
        uploaded_files = [_.get(FILE_NAME) for _ in uploaded_files_response.json().get(FILES_WRITTEN_DB)]
        file_paths = [FILES_DIR.joinpath(file_name) for file_name in uploaded_files if uploaded_files is not None]
        all_files_in_folder = [file.name for file in FILES_DIR.glob('*')]
        if uploaded_files is not None:
            for file in uploaded_files:
                assert file in all_files_in_folder, f"Can't find: {file} in files folder: {FILES_DIR}"
        # expected keys dictionary for search scenarios:
        expected_key_dictionary = {
            "all_db_files": files_in_db,
            "testfile2": [_ for _ in files_in_db if "testfile2" in _],
            "testfile3": [_ for _ in files_in_db if "testfile3" in _],
            "testfiles_3_2": [_ for _ in files_in_db if "testfile3" in _ or "testfile2" in _],
            "no_files": []
        }
        login_user_response = await ac.post(LOGIN, data=user_orm_login)
        assert login_user_response.status_code == 200, f"User: {user_orm_login} couldn't get {LOGIN}"
        # !!!! starting testing scenarios:
        for search_params, status, expected_key, name in scenarios:
            scenario_number += 1
            await log.ainfo(f"**************************************  SCENARIO: __ {scenario_number} __: {name}")
            response = await ac.get(
                test_url,
                params=search_params,
                headers={"Authorization": f"Bearer {login_user_response.json()['access_token']}"},
            )
            assert response.status_code == status, f"{user_orm_login} couldn't get {test_url}. Inf:{response.__dict__}"
            if response.status_code != 200:
                await log.ainfo(
                    f"SCENARIO: _{scenario_number}_ info: ",
                    login_data=user_orm_login,
                    params=search_params,
                    response=response.json(),
                    status=response.status_code,
                    wings_of_end=f"STATUS: {response.status_code}___ END of SCENARIO: ___ {scenario_number} ___ {name}"
                )
                continue
            response_attachment = response.headers.get("content-disposition").split(";")[1]
            response_content_decoded = response._content.decode(errors="ignore")
            search_results = []
            # if search_params.get(SEARCH_FILES_BY_NAME) is not None:
            for file in files_in_db:
                if file in response_content_decoded:
                    search_results += [file]
            expected = {  # expected values in scenario
                "total_files_in_db": len(files),
                "response_attachment": "archive.zip",
                "expected_key_dictionary": expected_key_dictionary[expected_key],
            }
            match_values = (
                # name_value, expected_value, exist_value
                ("Files in db total: ", expected.get("total_files_in_db"), len(files_in_db)),
                ("Files in db equals uploaded files: ", set(files_in_db), set(uploaded_files)),
                ("Content-disposition: ", expected.get("response_attachment"), response_attachment.split("_")[-1]),
                ("Search results: ", set(expected.get("expected_key_dictionary")), set(search_results)),
            )
            for name_value, expected_value, exist_value in match_values:
                assert expected_value == exist_value, f"{name_value} {exist_value} not as expected: {expected_value}"
            await log.awarning(
                f"SCENARIO: _{scenario_number}_ info: {name}",
                files_in_db=files_in_db,
                response_attachment=response_attachment,
                response_content_decoded=response_content_decoded,
                search_params=search_params,
                search_results=search_results,
                # uploaded_files=uploaded_files,
                # login_data=user_orm_login,
                # response=response.__dict__,
                wings_of_end=f"_________ END of SCENARIO: ___ {scenario_number}___ {name}"
            )
        await clean_test_database(async_db, FileAttached)  # clean db after each single test
        await delete_files_in_folder(file_paths)
        all_files_in_folder = [file.name for file in FILES_DIR.glob('*')]
        if uploaded_files is not None:
            for file in uploaded_files:
                assert file not in all_files_in_folder, f"{file} in files folder: {FILES_DIR}, but shouldn't"
    await clean_test_database(async_db, User)
