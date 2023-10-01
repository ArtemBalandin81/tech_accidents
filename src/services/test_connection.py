import asyncio
import requests
from time import sleep

from datetime import datetime

from src.api.constants import CONNECTION_TEST_URL


async def test_connection(CONNECTION_TEST_URL: str = "https://www.agidel-am.ru") -> dict[str, int | str]:  # TODO -> ???:
    """ Тестирует доступ к интернет и сохраняет случай простоя в случае отсутствия доступа."""
    status_code = requests.get(CONNECTION_TEST_URL).status_code
    result = {CONNECTION_TEST_URL: status_code, "time": datetime.now().isoformat(timespec='seconds')}
    print(result)
    return result


async def run_test_connection_asyncio():
    """ Запускает периодический процесс тестирование доступа к интернет."""
    while True:
        await asyncio.sleep(5)
        await test_connection()

# async def run_test_connection():  #TODO УДАЛИТЬ
#     """ Запускает периодический процесс тестирование доступа к интернет."""
#     await test_connection()
#     sleep(2)
#     await test_connection()
#     sleep(2)
#     await test_connection()