"""src/services/db_backup.py"""
import asyncio
from datetime import date
from pathlib import Path
import re
from shutil import copy2
from typing import Generator

from src.api.constants import *
from src.settings import settings


SERVICES_DIR = Path(__file__).resolve().parent.parent.parent
BACKUP_DIR = SERVICES_DIR.joinpath(settings.DB_BACKUP_DIR)


class DBBackupService:
    """
    Сервис для автоматического архивирования БД:
    self.db_path = app\db_backups\tech_accident_db_local.db
    """
    def __init__(self,) -> None:
        self.db_path = BACKUP_DIR.joinpath(settings.DATABASE_NAME)

    def check_backup_dir_exists(self, folder=BACKUP_DIR) -> None:  # Path - не мб асинхронным?
        """ Проверяет наличие каталога, и создает его если нет."""
        if not Path(folder).exists():
            folder.mkdir(parents=True, exist_ok=True)
            print("{}".format(DIR_CREATED))  # TODO заменить логгированием и вынести в константу

    def get_base_dir(self, folder=SERVICES_DIR) -> Path | str:  # Path - не мб асинхронным?
        """ Отдает путь к каталогу приложения."""
        return str(folder)

    def get_list_of_names_in_dir(self, folder=BACKUP_DIR) -> list | Generator:  # Path - не мб асинхронным?
        """ Возвращает список файлов в каталоге, соответсвующих регулярному выражению файла-даты."""
        self.check_backup_dir_exists(folder)
        return [re.findall(DATE_PATTERN, str(file)) for file in folder.glob("*.db")]
        # return folder.glob("*.db")  # если нужно вернуть итератор

    def make_copy_db(self, folder=BACKUP_DIR) -> None:
        """ Проверяет есть ли каталог для архивов БД и копирует архив в этот каталог."""
        try:
            copy2(SERVICES_DIR.joinpath(settings.DATABASE_NAME), BACKUP_DIR)
            self.db_path.rename(BACKUP_DIR.joinpath("{}{}".format(date.today(), ".db")))
            print("{}".format(FILE_SAVED))  # TODO заменить логгированием и вынести в константу
        except FileNotFoundError:
            print("{}".format(COPY_FILE_ERROR))  # TODO заменить логгированием и вынести в константу
        except FileExistsError:
            print("{}".format(FILE_EXISTS_ERROR))  # TODO заменить логгированием и вынести в константу
        if self.db_path.exists():
            Path(self.db_path).unlink()  # удаляем дублирующий tech_accident_db_local.db
            print("{}{}".format(settings.DATABASE_NAME, DELETED_OK))  # TODO заменить логгированием + константа
        total_db_files = self.get_list_of_names_in_dir(folder)
        if len(total_db_files) >= settings.MAX_DB_BACKUP_FILES:
            old_file_to_remove = "{}{}".format(min(total_db_files)[0], ".db")  # самый ранний файл: 2024-01-05.db
            Path(BACKUP_DIR.joinpath(old_file_to_remove)).unlink()
            print("{}{}".format(min(total_db_files)[0], DELETED_OK))  # TODO заменить логгированием + константа

    async def run_db_backup(self,) -> None:
        """Запускает периодический процесс создания копии БД."""
        while True:
            await asyncio.sleep(settings.SLEEP_DB_BACKUP)
            self.make_copy_db()
