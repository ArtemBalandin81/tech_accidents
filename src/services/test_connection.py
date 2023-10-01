import asyncio
import requests
from time import sleep

from datetime import datetime

from src.api.constants import CONNECTION_TEST_URL
SLEEP = 5


async def test_connection(CONNECTION_TEST_URL: str = "https://www.agidel-am.ru") -> dict[str, int | str]:  # TODO -> ???:
    """ Тестирует доступ к интернет и сохраняет случай простоя в случае отсутствия доступа."""
    status_code = requests.get(CONNECTION_TEST_URL).status_code
    result = {CONNECTION_TEST_URL: status_code, "time": datetime.now().isoformat(timespec='seconds')}
    print(result)
    return result


async def run_test_connection_asyncio(time_counter: int = 0):  #TODO после сбоя не перезапускается
    """ Запускает периодический процесс тестирование доступа к интернет."""
    try:
        while True:
            await asyncio.sleep(SLEEP)
            await test_connection()
            if time_counter != 0:
                print(f"простой составил: {time_counter}")
                # TODO фиксируется время простоя и заносится в БД
                # TODO нужно фиксировать время начало простоя и окончания
                time_counter = 0  # обнуляем счетчик, если соединение восстановилось
    except requests.exceptions.ConnectionError:
        print(f"connection_error: {ConnectionError}")
        time_counter += SLEEP
        print(f"time_counter: {time_counter}")
        await asyncio.sleep(SLEEP)
        await run_test_connection_asyncio(time_counter)  # рекурсией проверяем восстановление соединения + счетчик


        # 1. Запускаем счетчик секунд.
        # 2. Через каждые 5 сек проверяется связь
        #    2.1 Если связь есть - #TODO фиксируется время простоя и заносится в БД
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