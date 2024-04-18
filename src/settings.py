"""src/settings.py"""
from functools import lru_cache
from pathlib import Path
from urllib.parse import urljoin

# from pydantic import BaseSettings, validator  # УСТАРЕЛО!
from pydantic import validator
from pydantic_settings import BaseSettings
# from pydantic.tools import lru_cache  # УСТАРЕЛО!

BASE_DIR = Path(__file__).resolve().parent.parent


@lru_cache
def get_env_path() -> Path | None:
    import importlib

    try:
        importlib.import_module("dotenv")
    except ImportError:
        return
    if BASE_DIR.joinpath(".env").exists():
        return BASE_DIR.joinpath(".env")


class Settings(BaseSettings):
    """Настройки проекта."""
    APP_TITLE: str = "Учет фактов простоя ИС"
    APP_DESCRIPTION: str = "Журнал учета фактов простоя информационной системы УК ПИФ"
    APPLICATION_URL: str = "localhost"
    DEBUG: bool = False
    ROOT_PATH: str = "/api"
    SECRET_KEY: str = "secret_key"
    TOKEN_AUTH_LIFETIME_SEC: int = 60 * 60 * 24 * 5

    # USE_NGROK: bool = False

    # Параметры подключения к БД
    DATABASE_URL: str = "sqlite+aiosqlite:///./tech_accident_db_local.db"
    DATABASE_NAME: str = "tech_accident_db_local.db"
    DB_BACKUP: bool = True
    DB_BACKUP_DIR: str = "db_backups"
    MAX_DB_BACKUP_FILES: int = 50
    SLEEP_DB_BACKUP: int = 60 * 60 * 24
    TIMEZONE_OFFSET: int = 5
    # POSTGRES_DB: str
    # POSTGRES_USER: str
    # POSTGRES_PASSWORD: str
    # DB_HOST: str = "localhost"
    # DB_PORT: int = 5432

    # Настройки логирования
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str | Path = BASE_DIR.joinpath("logs")
    LOG_FILE: str = "app.log"
    LOG_FILE_SIZE: int = 10 * 2**20
    LOG_FILES_TO_KEEP: int = 5

    # Настройки тестирования доступа к Интернет
    SLEEP_TEST_CONNECTION: int = 20

    # Настройки ENUM-класса персонала для постановки задач
    STAFF: str = (
        '{"99": "unload_users@please_check.env",'
        ' "100": "error_of_load_users@please_check.env",'
    )
    # Настройки ENUM-класса тех.процессов для фиксации простоев
    TECH_PROCESS: str = (
        '{"DU_25": "25",'
        ' "SPEC_DEP_26": "26",'
        ' "CLIENTS_27": "27",'
    )
    # Настройки ENUM-класса угроз для фиксации простоев
    RISK_SOURCE: str = (
        '{"99": "unload_risk_source_please_check.env.",'
        ' "100": "error_of_load_risk_accident_source@please_check.env",'
        ' "ROUTER": "Риск инцидент: сбой в работе рутера.",'
    )

    @property
    def database_url(self) -> str:
        """Получить ссылку для подключения к DB."""
        # return (
        #     "postgresql+asyncpg://"
        #     f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
        #     f"@{self.DB_HOST}:{self.DB_PORT}/{self.POSTGRES_DB}"
        # )
        return Settings.DATABASE_URL  # "sqlite+aiosqlite:///./tech_accident_db_local.db"

    # class Config:  # Устарело TODO убрать
    #     #env_file = get_env_path()
    #     env_file = '.env'

    # Настройки бота
    #BOT_TOKEN: str
    #BOT_WEBHOOK_MODE: bool = False


@lru_cache()
def get_settings():
    # return Settings()  # Устарело
    return Settings(_env_file=get_env_path())  # type: ignore


settings = get_settings()
