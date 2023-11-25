"""src/services/register_connection_errors.py"""
import asyncio
import contextlib
import requests

from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Generator

from src.api.constants import CONNECTION_TEST_URL_AGI, CONNECTION_TEST_URL_YA, SLEEP_TEST_CONNECTION, TZINFO
from src.core.db.db import get_session
from src.core.db.models import Suspension
from src.core.db.repository.suspension import SuspensionRepository


class ConnectionErrorService:
    """Сервис для автоматической регистрации случаев простоя."""
    def __init__(self, sessionmaker: Generator[AsyncSession, None, None] = get_session) -> None:
        self._sessionmaker = contextlib.asynccontextmanager(sessionmaker)
        self.suspension_example = {
            "datetime_start": datetime.now(TZINFO) - timedelta(minutes=5),
            "datetime_finish": datetime.now(TZINFO),
            "risk_accident": "Риск инцидент: сбой в работе рутера.",
            "tech_process": 25,
            "description": "Кратковременный сбой доступа в Интернет.",
            "implementing_measures": "Перезагрузка оборудования.",
            "user_id": 2,  # ПОД "user_id" = 2 подразумевается работа робота автомата фиксации простоев TODO хрупко!
        }

    async def check_connection(
            self,
            CONNECTION_TEST_URL_AGI: str = "https://www.agidel-am.ru"
    ) -> dict[str, int | str]:
        """ Проверяет наличие доступа к интернет."""
        try:
            status_code_url_agidel = requests.get(CONNECTION_TEST_URL_AGI).status_code
        except requests.exceptions.ConnectionError:  # если ошибка соединения с сайтом Агидель
            status_code_url_ya = requests.get(CONNECTION_TEST_URL_YA).status_code
            result = {
                CONNECTION_TEST_URL_AGI: "ConnectionError",
                CONNECTION_TEST_URL_YA: status_code_url_ya,
                "time": datetime.now(TZINFO).isoformat(timespec='seconds')
            }
            print(result)  # TODO заменить логированием
            return result
        result = {
            CONNECTION_TEST_URL_AGI: status_code_url_agidel,
            CONNECTION_TEST_URL_YA: "Didn't try, suppose OK!",
            "time": datetime.now(TZINFO).isoformat(timespec='seconds')
        }
        print(result)  #TODO заменить логированием
        return result

    async def run_create_suspension(self, suspension_object: dict | None) -> None:
        """ Запускает тестовое сохранение случая простоя в БД."""
        if suspension_object is None:
            suspension_object = self.suspension_example
        suspension = Suspension(**suspension_object)
        async with self._sessionmaker() as session:
            suspension_repository = SuspensionRepository(session)
            await suspension_repository.create(suspension)
            print(f"Сохранен случай простоя в БД: {suspension}")  #TODO заменить логированием

    async def run_check_connection(
            self,
            time_counter: int = SLEEP_TEST_CONNECTION,
            suspension_start: bool | datetime = None,
    ) -> None:
        """ Запускает периодический процесс тестирование доступа к интернет и сохранение в БД простоев."""
        try:
            while True:
                await asyncio.sleep(SLEEP_TEST_CONNECTION)
                await self.check_connection(CONNECTION_TEST_URL_AGI)
                if time_counter != SLEEP_TEST_CONNECTION:  # Начальный счетчик простоя = интервалу проверки соединения
                    print(f"suspension_start: {suspension_start}")  #TODO заменить логированием
                    print(f"datetime_finish: {datetime.now(TZINFO)}")
                    print(f"счетчик простоя: {time_counter}")
                    suspension = self.suspension_example  # фиксируется время простоя и заносится в БД
                    suspension["datetime_start"] = suspension_start
                    suspension["datetime_finish"] = datetime.now(TZINFO)
                    await self.run_create_suspension(suspension)
                    time_counter = SLEEP_TEST_CONNECTION  # обнуляем счетчик, если соединение восстановилось
                    suspension_start = None  # обнуляем счетчик времени старта простоя
        except requests.exceptions.ConnectionError:  # если ошибка соединения
            if suspension_start is not None:  # если не первый старт фиксации простоя
                time_counter += SLEEP_TEST_CONNECTION
                suspension_start = suspension_start
                print(f"time_counter: {time_counter} / error: {ConnectionError}")
                await asyncio.sleep(SLEEP_TEST_CONNECTION)  # задаем задержку проверки соединения
                await self.run_check_connection(time_counter, suspension_start)  # рекурсивно проверяем соединение
            suspension_start = datetime.now(TZINFO)
            time_counter += SLEEP_TEST_CONNECTION
            print(f"1st_time_counter: {time_counter} / suspension_START: {suspension_start}")  #TODO заменить логир-м
            await asyncio.sleep(SLEEP_TEST_CONNECTION)
            await self.run_check_connection(time_counter, suspension_start)
