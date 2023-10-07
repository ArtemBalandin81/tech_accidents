import asyncio
import contextlib
import requests

from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Generator

from src.api.constants import CONNECTION_TEST_URL
from src.core.db.db import get_session
from src.core.db.models import Suspension
from src.core.db.repository.suspension import SuspensionRepository

SLEEP: int = 5


class ConnectionErrorService:
    """Сервис для автоматической регистрации случаев простоя."""
    def __init__(self, sessionmaker: Generator[AsyncSession, None, None] = get_session) -> None:
        self._sessionmaker = contextlib.asynccontextmanager(sessionmaker)
        self.suspension_example = {
            "datetime_start": datetime.now() - timedelta(minutes=5),
            "datetime_finish": datetime.now(),
            "risk_accident": "Риск инцидент: сбой в работе рутера.",
            "tech_process": 25,
            "description": "Кратковременный сбой доступа в Интернет.",
            "implementing_measures": "Перезагрузка оборудования.",
            "user_id": 2,  # ПОД "user_id" = 2 подразумевается работа робота автомата фиксации простоев TODO хрупко!
        }

    async def check_connection(self, CONNECTION_TEST_URL: str = "https://www.agidel-am.ru") -> dict[str, int | str]:
        """ Проверяет наличие доступа к интернет."""
        status_code = requests.get(CONNECTION_TEST_URL).status_code
        result = {CONNECTION_TEST_URL: status_code, "time": datetime.now().isoformat(timespec='seconds')}
        print(result)
        return result

    async def run_create_suspension(self, suspension_object: dict | None):  # TODO что на выходе -> ? -> Suspension -> None
        """ Запускает тестовое сохранение случая простоя в БД."""
        if suspension_object is None:
            suspension_object = self.suspension_example
        suspension = Suspension(**suspension_object)
        async with self._sessionmaker() as session:
            suspension_repository = SuspensionRepository(session)
            await suspension_repository.create(suspension)
            print(f"Сохранен случай простоя в БД: {suspension}")

    async def run_check_connection(
            self,
            time_counter: int = SLEEP,
            suspension_start: bool | datetime = None,
    ):  # TODO что на выходе -> ?
        """ Запускает периодический процесс тестирование доступа к интернет и сохранение в БД простоев."""
        try:
            while True:
                await asyncio.sleep(SLEEP)
                await self.check_connection()
                if time_counter != SLEEP:
                    print(f"suspension_start: {suspension_start}")  #TODO заменить логированием
                    print(f"datetime_finish: {datetime.now()}")
                    print(f"счетчик простоя: {time_counter}")
                    suspension = self.suspension_example  # фиксируется время простоя и заносится в БД
                    suspension["datetime_start"] = suspension_start
                    suspension["datetime_finish"] = datetime.now()
                    await self.run_create_suspension(suspension)
                    time_counter = SLEEP  # обнуляем счетчик, если соединение восстановилось
                    suspension_start = None  # обнуляем счетчик времени старта простоя
        except requests.exceptions.ConnectionError:
            if suspension_start is not None:  # если не первый старт фиксации простоя
                time_counter += SLEEP
                suspension_start = suspension_start
                print(f"time_counter: {time_counter} / error: {ConnectionError}")
                await asyncio.sleep(SLEEP)  # задаем задержку проверки соединения
                await self.run_check_connection(time_counter, suspension_start)  # рекурсивно проверяем соединение
            suspension_start = datetime.now()
            time_counter += SLEEP
            print(f"1st_time_counter: {time_counter} / suspension_START: {suspension_start}")
            await asyncio.sleep(SLEEP)
            await self.run_check_connection(time_counter, suspension_start)
