"""src/services/register_connection_errors.py"""
import asyncio
import contextlib
import requests
import structlog

from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Generator

from src.api.constants import CONNECTION_TEST_URL_BASE, CONNECTION_TEST_URL_YA, TZINFO
from src.core.db.db import get_session
from src.core.db.models import Suspension
from src.core.db.repository.suspension import SuspensionRepository
from src.settings import settings


log = structlog.get_logger().bind(file_name=__file__)


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
            "user_id": 2,  # ПОД "user_id" = 2 скрывается работа автомата фиксации простоев TODO хрупко!
        }

    async def check_connection(
            self,
            CONNECTION_TEST_URL_BASE: str = "https://www.agidel-am.ru"
    ) -> dict[str, int | str]:
        """ Проверяет наличие доступа к интернет."""
        try:
            status_code_base_url = requests.get(CONNECTION_TEST_URL_BASE).status_code
        # если ошибка соединения с базовым сайтом, то тест сайта Яндекс
        # если и сайта Яндекс не доступен - в run_check_connection() вызывается except!
        except requests.exceptions.ConnectionError:
            await log.aerror("Failed_get_url.", url=CONNECTION_TEST_URL_BASE)
            status_code_url_ya = requests.get(CONNECTION_TEST_URL_YA).status_code
            info_connections = {
                CONNECTION_TEST_URL_BASE: "ConnectionError",
                CONNECTION_TEST_URL_YA: status_code_url_ya,
                "time": datetime.now(TZINFO).isoformat(timespec='seconds')
            }
            await log.ainfo("Info_connections", info_connections=info_connections)
            return info_connections
        info_connections = {
            CONNECTION_TEST_URL_BASE: status_code_base_url,
            CONNECTION_TEST_URL_YA: "Didn't try, suppose OK!",
            "time": datetime.now(TZINFO).isoformat(timespec='seconds')
        }
        await log.ainfo("Info_connections", info_connections=info_connections)
        return info_connections

    async def run_create_suspension(self, suspension_object: dict | None) -> None:
        """ Запускает тестовое сохранение случая простоя в БД."""
        if suspension_object is None:
            suspension_object = self.suspension_example
        suspension = Suspension(**suspension_object)
        async with self._sessionmaker() as session:
            suspension_repository = SuspensionRepository(session)
            await suspension_repository.create(suspension)
            await log.ainfo("Suspension_loaded_in_db.", suspension=suspension)

    async def run_check_connection(
            self,
            time_counter: int = settings.SLEEP_TEST_CONNECTION,
            suspension_start: bool | datetime = None,
    ) -> None:
        """ Запускает периодический процесс тестирование доступа к интернет и сохранение в БД простоев."""
        try:
            while True:
                await asyncio.sleep(settings.SLEEP_TEST_CONNECTION)
                await self.check_connection(CONNECTION_TEST_URL_BASE)
                if time_counter != settings.SLEEP_TEST_CONNECTION:  # Нач. счетчик простоя = интервалу теста соединения
                    await log.ainfo(
                        "Create_suspension.",
                        start=str(suspension_start),
                        finish=datetime.now(TZINFO).isoformat(timespec='seconds'),
                        counter=time_counter
                    )
                    suspension = self.suspension_example  # фиксируется время простоя и заносится в БД
                    suspension["datetime_start"] = suspension_start
                    suspension["datetime_finish"] = datetime.now(TZINFO)
                    await self.run_create_suspension(suspension)
                    time_counter = settings.SLEEP_TEST_CONNECTION  # обнуляем счетчик, если соединение восстановилось
                    suspension_start = None  # обнуляем счетчик времени старта простоя
        except requests.exceptions.ConnectionError:  # если ошибка соединения
            await log.aerror("Failed_get_url.", url=CONNECTION_TEST_URL_YA)
            if suspension_start is not None:  # если не первый старт фиксации простоя
                time_counter += settings.SLEEP_TEST_CONNECTION
                suspension_start = suspension_start
                await log.ainfo("Time_counter.", counter=time_counter, err=ConnectionError, url=CONNECTION_TEST_URL_YA)
                await asyncio.sleep(settings.SLEEP_TEST_CONNECTION)  # задаем задержку проверки соединения
                await self.run_check_connection(time_counter, suspension_start)  # рекурсивно проверяем соединение
            suspension_start = datetime.now(TZINFO)
            time_counter += settings.SLEEP_TEST_CONNECTION
            await log.ainfo("First_time_counter.", counter=time_counter, suspension_start=str(suspension_start))
            await asyncio.sleep(settings.SLEEP_TEST_CONNECTION)
            await self.run_check_connection(time_counter, suspension_start)
