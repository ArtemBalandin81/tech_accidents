"""src/services/db_backup.py"""

import asyncio
import re
from datetime import date
from pathlib import Path
from shutil import copy2
from typing import Generator

import structlog
from src.api.constants import *
from src.settings import settings

log = structlog.get_logger()

SERVICES_DIR = Path(__file__).resolve().parent.parent.parent
BACKUP_DIR = SERVICES_DIR.joinpath(settings.DB_BACKUP_DIR)


class DBBackupService:
    """
    Сервис для автоматического архивирования БД:
    self.db_path = app/db_backups/tech_accident_db_local.db
    """
    def __init__(self,) -> None:
        self.db_path = BACKUP_DIR.joinpath(settings.DATABASE_NAME)

    async def check_folder_exists(self, folder=BACKUP_DIR) -> None:
        """ Проверяет наличие каталога, и создает его если нет."""
        if not Path(folder).exists():
            folder.mkdir(parents=True, exist_ok=True)
            await log.ainfo("{}".format(DIR_CREATED), folder=folder)

    async def get_list_of_names_in_dir(self, folder=BACKUP_DIR) -> list | Generator:
        """ Возвращает список файлов в каталоге, соответсвующих регулярному выражению файла-даты."""
        await self.check_folder_exists(folder)
        return [re.findall(DATE_PATTERN, str(file)) for file in folder.glob("*.db")]
        # return folder.glob("*.db")  # if is needed to return iterator

    async def make_copy_db(self, folder=BACKUP_DIR) -> None:
        """ Проверяет есть ли каталог для архивов БД и копирует архив в этот каталог."""
        db_to_backup = SERVICES_DIR.joinpath(settings.DATABASE_NAME)
        try:
            await self.check_folder_exists()
            copy2(db_to_backup, BACKUP_DIR)
            new_backup_db = self.db_path.rename(BACKUP_DIR.joinpath("{}{}".format(date.today(), ".db")))
            await log.ainfo("{}".format(FILE_SAVED), file=new_backup_db)
        except FileNotFoundError:
            await log.aerror("{}".format(COPY_FILE_ERROR), file=str(db_to_backup))
        except FileExistsError:
            await log.aerror("{}".format(FILE_EXISTS_ERROR), file=str(db_to_backup))
        if self.db_path.exists():
            Path(self.db_path).unlink()  # delete duplicate tech_accident_db_local.db
            await log.ainfo("{}{}".format(settings.DATABASE_NAME, DELETED_OK), file=self.db_path)
        total_db_files = await self.get_list_of_names_in_dir(folder)
        if len(total_db_files) >= settings.MAX_DB_BACKUP_FILES:
            old_file_to_remove = "{}{}".format(min(total_db_files)[0], ".db")
            Path(BACKUP_DIR.joinpath(old_file_to_remove)).unlink()  # delete the oldest backup
            await log.ainfo("{}{}".format(min(total_db_files)[0], DELETED_OK), old_file_to_remove=old_file_to_remove)

    async def run_db_backup(self,) -> None:
        """Запускает периодический процесс создания копии БД."""
        while True:
            await asyncio.sleep(settings.SLEEP_DB_BACKUP)
            await self.make_copy_db()
