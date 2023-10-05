import asyncio
import requests
from time import sleep

from datetime import datetime, timedelta
from fastapi import Depends

from src.api.constants import CONNECTION_TEST_URL
from src.api.services import SuspensionService
#from src.core.db.models import User  #TODO user передаем определенный, автомат
from src.core.db.user import current_superuser, current_user, unauthorized_user

SLEEP: int = 5
AUTO_FIX_USER: int = 2  #TODO user передаем определенный, автомат

async def test_connection(CONNECTION_TEST_URL: str = "https://www.agidel-am.ru") -> dict[str, int | str]:  # TODO -> ???:
    """ Тестирует доступ к интернет и сохраняет случай простоя в случае отсутствия доступа."""
    status_code = requests.get(CONNECTION_TEST_URL).status_code
    result = {CONNECTION_TEST_URL: status_code, "time": datetime.now().isoformat(timespec='seconds')}
    print(result)
    return result


async def run_test_connection_asyncio(
        time_counter: int = SLEEP,
        suspension_start: bool | datetime = None,
        #suspension_service: SuspensionService = Depends(),
        #user: User = Depends(current_user),  #TODO user передаем определенный, автомат
        user: int = AUTO_FIX_USER
):  # TODO что на выходе -> ?
    """ Запускает периодический процесс тестирование доступа к интернет."""
    try:
        while True:
            await asyncio.sleep(SLEEP)
            await test_connection()
            if time_counter != SLEEP:
                print(f"suspension_start: {suspension_start}")  # а это правильный простой
                print(f"datetime_finish: {datetime.now()}")
                print(f"счетчик простоя: {time_counter}")  # счетчик простоя сильно занижен
                # TODO фиксируется время простоя и заносится в БД
                suspension_object = {  # TODO используй typedict  #TODO в константы зашить
                    "datetime_start": suspension_start,
                    "datetime_finish": datetime.now(),
                    "risk_accident": "Риск инцидент: сбой в работе рутера.",
                    "tech_process": 25,
                    "description": "Кратковременный сбой доступа в Интернет.",
                    "implementing_measures": "Перезагрузка оборудования.",
                }
                #suspension_service = SuspensionService()
                #await suspension_service.actualize_object(suspension_id=None, in_object=suspension_object, user=user)
                time_counter = SLEEP  # обнуляем счетчик, если соединение восстановилось
                suspension_start = None  # обнуляем счетчик времени старта простоя
    except requests.exceptions.ConnectionError:
        if suspension_start is None:
            print(f"connection_error_1st: {ConnectionError}")
            suspension_start = datetime.now()
            time_counter += SLEEP
            print(f"time_counter_1st: {time_counter}")
            print(f"suspension_REAL_START: {suspension_start}")
            await asyncio.sleep(SLEEP)
            await run_test_connection_asyncio(time_counter, suspension_start)
        else:
            print(f"connection_error: {ConnectionError}")
            time_counter += SLEEP
            suspension_start = suspension_start
            print(f"time_counter: {time_counter}")
            await asyncio.sleep(SLEEP)
            await run_test_connection_asyncio(time_counter, suspension_start)  # рекурсией проверяем восстановление соединения + счетчик

async def run_test_create_suspension(
        time_counter: int = SLEEP,
        suspension_start: bool | datetime = None,
        user: int = AUTO_FIX_USER,
):  # TODO что на выходе -> ?
    """ Запускает периодический процесс сохранения простоя в БД."""
    suspension_object = {
        "datetime_start": datetime.now() - timedelta(minutes=5),
        "datetime_finish": datetime.now(),
        "risk_accident": "Риск инцидент: сбой в работе рутера.",
        "tech_process": 25,
        "description": "Кратковременный сбой доступа в Интернет.",
        "implementing_measures": "Перезагрузка оборудования.",
    }
    suspension_service = SuspensionService()
    await suspension_service.actualize_object(suspension_id=None, in_object=suspension_object, user=user)



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