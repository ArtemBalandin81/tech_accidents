"""
src/settings.py
(.env in priority - check it before!)
"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings

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
    ANALYTICS_INTERVAL: int = 30  # time shift (in days) to display total suspensions
    APP_TITLE: str = "Учет фактов простоя ИС"
    APP_DESCRIPTION: str = "Журнал учета фактов простоя информационной системы УК ПИФ"
    APPLICATION_URL: str = "localhost"
    CREATE_FROM_TIME: int = 5  # time shift (in mins) when creating suspensions in forms
    CREATE_TO_TIME: int = 1  # time shift (in mins) when creating suspensions in forms
    DEFAULT_TASK_DEADLINE: int = 7  # typical task deadline in days
    DEBUG: bool = False
    FILES_DOWNLOAD_DIR: str = "uploaded_files"
    FILE_TYPE_DOWNLOAD: str | list = ("doc", "docx", "xls", "xlsx", "img", "png", "txt", "pdf", "jpeg")
    MAX_FILE_SIZE_DOWNLOAD: int = 10000  # Max available file size in kb
    ROOT_PATH: str = "/api"
    SECRET_KEY: str = "secret_key"
    SUSPENSION_DISPLAY_TIME: int = 60 * 24  # in mins as part of a day
    TOKEN_AUTH_LIFETIME_SEC: int = 60 * 60 * 24 * 5

    # Database connection preferences (.env in priority - check it before!)
    DATABASE_URL: str = "sqlite+aiosqlite:///./tech_accident_db_local.db"
    DATABASE_URL_TEST: str = "sqlite+aiosqlite:///./test_db.db"
    DATABASE_NAME: str = "tech_accident_db_local.db"
    DB_BACKUP: bool = True
    DB_BACKUP_DIR: str = "db_backups"
    ECHO: bool = False  # echo=True display SQL-queries in console for main DB
    ECHO_TEST_DB: bool = False  # echo=True display SQL-queries in console for test DB
    MAX_DB_BACKUP_FILES: int = 50
    SLEEP_DB_BACKUP: int = 60 * 60 * 24
    TIMEZONE_OFFSET: int = 5
    # POSTGRES_DB: str
    # POSTGRES_USER: str
    # POSTGRES_PASSWORD: str
    # DB_HOST: str = "localhost"
    # DB_PORT: int = 5432

    # Logging preferences (.env in priority - check it before!)
    FILE_NAME_IN_LOG: bool = False  # If true: structlog.get_logger().bind(file_name=__file__)
    JSON_LOGS: bool = False  # true: logs in json with JSONRenderer | false: colored logs with ConsoleRenderer
    LOG_LEVEL: str = "WARN"  # .env in priority: (WARN, INFO, DEBUG)
    LOG_DIR: str | Path = BASE_DIR.joinpath("logs")
    LOG_FILE: str = "app.log"
    LOG_FILE_SIZE: int = 10 * 2**20
    LOG_FILES_TO_KEEP: int = 5

    # Internet access test preferences (.env in priority - check it before!)
    CONNECTION_TEST_URL_BASE: str = "https://www.agidel-am.ru"
    CONNECTION_TEST_URL_2: str = "https://www.ya.ru"
    SLEEP_TEST_CONNECTION: int = 20

    # Download and delete files form ENUM-class preferences (.env in priority - check it before!)
    CHOICE_DOWNLOAD_FILES: str = '{"JSON": "json", "FILES": "files"}'
    CHOICE_REMOVE_FILES_UNUSED: str = (
        '{"DB_UNUSED": "unused_in_db",'
        ' "DB_UNUSED_REMOVE": "remove_unused_in_db",'
        ' "FOLDER_UNUSED": "unused_in_folder",'
        ' "FOLDER_UNUSED_REMOVE": "delete_unused_in_folder"}'
    )

    # Staff ENUM-class preferences for tasks (.env in priority - check it before!)
    BOT_USER: int = 2
    STAFF: str = (
        '{"99": "unload_users@please_check.env",'
        ' "100": "error_of_load_users@please_check.env"}'
    )
    # Tech-processes suspensions ENUM-class preferences (.env in priority - check it before!)
    INTERNET_ACCESS_TECH_PROCESS: int = 25
    TECH_PROCESS: str = (
        '{"DU_25": "25",'
        ' "SPEC_DEP_26": "26",'
        ' "CLIENTS_27": "27"}'
    )
    # Risk sources ENUM-class preferences (.env in priority - check it before!)
    RISK_SOURCE: str = (
        '{"99": "unload_risk_source_please_check.env.",'
        ' "100": "error_of_load_risk_accident_source@please_check.env",'
        ' "ROUTER": "Риск инцидент: сбой в работе рутера."}'
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


@lru_cache()
def get_settings():
    return Settings(_env_file=get_env_path())  # type: ignore


settings = get_settings()
