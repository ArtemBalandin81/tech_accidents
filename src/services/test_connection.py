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


async def run_test_connection_asyncio():  #TODO после сбоя не перезапускается
    """ Запускает периодический процесс тестирование доступа к интернет."""
    counter = 0
    try:
        while True:
            await asyncio.sleep(5)
            await test_connection()
    except requests.exceptions.ConnectionError:
        print(f"connection_error: {ConnectionError}")
        await asyncio.sleep(5)
        await run_test_connection_asyncio() #TODO счетчик простоя

        # counter += 1
        # print(f"counter: {counter}")


        # 1. Запускаем счетчик секунд.  #TODO счетчик простоя
        # 2. Через каждые 5 сек проверяется связь
        #    2.1 Если связь есть - фиксируется время простоя и заносится в БД
        #    2.2 Если связи нет, то счетчик продолжает бежать
        # 3. Нужно каким-то образом перезапускать run_test_connection_asyncio после обрыва связи



    #requests.exceptions.ConnectionError
    # while True:
    #     await asyncio.sleep(5)
    #     await test_connection()




# async def run_test_connection():  #TODO УДАЛИТЬ
#     """ Запускает периодический процесс тестирование доступа к интернет."""
#     await test_connection()
#     sleep(2)
#     await test_connection()
#     sleep(2)
#     await test_connection()