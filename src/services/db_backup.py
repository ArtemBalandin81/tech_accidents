"""src/services/db_backup.py"""
from datetime import datetime, timedelta
from pathlib import Path

# todo BACKUP_DIR - вынести в переменные окружения
# todo заменить путь на константы также из переменных окружения
# todo не забыть флажок False автоматического бэкапа БД
# BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent  # "app_folder": "C:\\Dev"
BASE_DIR = Path(__file__).resolve().parent.parent.parent
#BACKUP_DIR = BASE_DIR.joinpath("db_backups").joinpath("tech_accident_backups")
BACKUP_DIR = BASE_DIR.joinpath("db_backups")

# print(BASE_DIR)
# print(BACKUP_DIR)
# print(Path(BACKUP_DIR).exists())
class DBBackupService:  # с/dev/_db_backup/tech_accident_backups/01-01-2024.db
    """Сервис для автоматического архивирования БД."""
    # def __init__(self,) -> None:

    def check_backup_dir(self, folder=BACKUP_DIR) -> None:  #todo async? Path - не мб асинхронным
        """ Проверяет наличие каталога для бэкапа БД, и создает его если нет."""
        if not Path(folder).exists():
            folder.mkdir(parents=True, exist_ok=True)

    def get_base_dir(self, folder=BASE_DIR) -> Path | str:  #todo async? Path - не мб асинхронным
        """ Отдает путь к каталогу приложения."""
        return str(folder)

    def make_copy_db(self) -> None:
        """ Проверяет есть ли каталог для архивов БД и копирует архив в этот каталог."""
        pass

# test = DBBackupService()
# test.check_backup_dir(BACKUP_DIR)
# print(test.get_base_dir())
