from pathlib import Path
from urllib.parse import urljoin

from pydantic import BaseSettings, validator
from pydantic.tools import lru_cache

BASE_DIR = Path(__file__).resolve().parent.parent


@lru_cache
def get_env_path() -> Path | None:
    import importlib

    try:
        importlib.import_module("dotenv")
    except ImportError:
        return
    if Path.exists(BASE_DIR / ".env"):
        return BASE_DIR / ".env"


class Settings(BaseSettings):
    """Настройки проекта."""

    # APP_TITLE: str = 'Учет фактов простоя ИС'  # Если настройка не из .env
    app_title: str
    app_description: str

    APPLICATION_URL: str = "localhost"
    SECRET_KEY: str = "secret_key"
    ROOT_PATH: str = "/api"
    DEBUG: bool = False
    #USE_NGROK: bool = False

    class Config:
        env_file = get_env_path()
        #env_file = '.env'

    # Параметры подключения к БД
    # POSTGRES_DB: str
    # POSTGRES_USER: str
    # POSTGRES_PASSWORD: str
    # DB_HOST: str = "localhost"
    # DB_PORT: int = 5432

    # Настройки бота
    #BOT_TOKEN: str
    #BOT_WEBHOOK_MODE: bool = False

    # Настройки логирования
    # LOG_LEVEL: str = "INFO"
    # LOG_DIR: str | Path = BASE_DIR / "logs"
    # LOG_FILE: str = "app.log"
    # LOG_FILE_SIZE: int = 10 * 2**20
    # LOG_FILES_TO_KEEP: int = 5

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()