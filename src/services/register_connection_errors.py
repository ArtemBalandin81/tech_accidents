"""src/services/register_connection_errors.py"""
import asyncio
import contextlib
from datetime import datetime, timedelta
from typing import Generator

import requests
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.constants import (FAILED_GET_URL, FIRST_COUNTER, INFO_CONNECTIONS,
                               INTERNET_ERROR, MEASURES, ROUTER_ERROR,
                               SUPPOSE_OK, SUSPENSION_CREATED,
                               SUSPENSION_DB_LOADED, TIME_COUNTER, TIME_INFO,
                               TZINFO, URL_CONNECTION_ERROR)
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
            "risk_accident": ROUTER_ERROR,
            "tech_process": settings.INTERNET_ACCESS_TECH_PROCESS,
            "description": INTERNET_ERROR,
            "implementing_measures": MEASURES,
            "user_id": settings.BOT_USER,  # todo ПОД "user_id" = 2 скрывается id бота фиксации простоев - хрупко!
        }

    async def check_connection(
            self,
            CONNECTION_TEST_URL_BASE: str = settings.CONNECTION_TEST_URL_BASE,
            CONNECTION_TEST_URL_2: str = settings.CONNECTION_TEST_URL_2
    ) -> dict[str, int | str]:
        """ Проверяет наличие доступа к интернет."""
        try:
            status_code_base_url = requests.get(CONNECTION_TEST_URL_BASE).status_code
        # если ошибка соединения с базовым сайтом, то тест сайта Яндекс
        # если и сайта Яндекс не доступен - в run_check_connection() вызывается except!
        except requests.exceptions.ConnectionError:
            await log.aerror(FAILED_GET_URL, url=CONNECTION_TEST_URL_BASE)
            status_code_url_ya = requests.get(CONNECTION_TEST_URL_2).status_code
            info_connections = {
                CONNECTION_TEST_URL_BASE: URL_CONNECTION_ERROR,
                CONNECTION_TEST_URL_2: status_code_url_ya,
                TIME_INFO: datetime.now(TZINFO).isoformat(timespec='seconds')
            }
            await log.ainfo(INFO_CONNECTIONS, info_connections=info_connections)
            return info_connections
        info_connections = {
            CONNECTION_TEST_URL_BASE: status_code_base_url,
            CONNECTION_TEST_URL_2: SUPPOSE_OK,
            TIME_INFO: datetime.now(TZINFO).isoformat(timespec='seconds')
        }
        await log.ainfo(INFO_CONNECTIONS, info_connections=info_connections)
        return info_connections

    async def run_create_suspension(self, suspension_object: dict | None) -> None:
        """ Запускает тестовое сохранение случая простоя в БД."""
        if suspension_object is None:
            suspension_object = self.suspension_example
        suspension = Suspension(**suspension_object)
        async with self._sessionmaker() as session:
            suspension_repository = SuspensionRepository(session)
            await suspension_repository.create(suspension)
            await log.ainfo(SUSPENSION_DB_LOADED, suspension=suspension)

    async def run_check_connection(
            self,
            time_counter: int = settings.SLEEP_TEST_CONNECTION,
            suspension_start: bool | datetime = None,
    ) -> None:
        """ Запускает периодический процесс тестирование доступа к интернет и сохранение в БД простоев."""
        try:
            while True:
                await asyncio.sleep(settings.SLEEP_TEST_CONNECTION)
                await self.check_connection(settings.CONNECTION_TEST_URL_BASE, settings.CONNECTION_TEST_URL_2)
                if time_counter != settings.SLEEP_TEST_CONNECTION:  # Нач. счетчик простоя = интервалу теста соединения
                    await log.ainfo(
                        SUSPENSION_CREATED,
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
            await log.aerror(FAILED_GET_URL, url=settings.CONNECTION_TEST_URL_2)
            if suspension_start is not None:  # если не первый старт фиксации простоя
                time_counter += settings.SLEEP_TEST_CONNECTION
                suspension_start = suspension_start
                await log.ainfo(
                    TIME_COUNTER,
                    counter=time_counter,
                    err=ConnectionError,
                    url=settings.CONNECTION_TEST_URL_2
                )
                await asyncio.sleep(settings.SLEEP_TEST_CONNECTION)  # задаем задержку проверки соединения
                await self.run_check_connection(time_counter, suspension_start)  # рекурсивно проверяем соединение
            suspension_start = datetime.now(TZINFO)
            time_counter += settings.SLEEP_TEST_CONNECTION
            await log.ainfo(FIRST_COUNTER, counter=time_counter, suspension_start=str(suspension_start))
            await asyncio.sleep(settings.SLEEP_TEST_CONNECTION)
            await self.run_check_connection(time_counter, suspension_start)
