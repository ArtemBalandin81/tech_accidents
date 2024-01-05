"""src/api/endpoints/test_router.py"""
import requests

from fastapi import APIRouter, Query, Depends
from pathlib import Path

from src.api.constants import ANALYTIC_TO_TIME
from src.core.db.user import current_superuser
from src.services.db_backup import DBBackupService

test_router = APIRouter()

@test_router.get("/test_get_url", description="Проверка доступа к сайту.")
def test_get_url(
    url: str = Query(..., example="https://www.agidel-am.ru"),
) -> dict[str, int | str]:
    status_code = requests.get(url).status_code
    return {url: status_code, "time": ANALYTIC_TO_TIME}


# todo должно проверяться, что файл-бэкап создался - тогда в ответе - ОК, или ошибка
# todo возвращать схему пайдентик (переделать ответ под нее)
# todo ("/db_backup", description="Бэкап БД.", dependencies=[Depends(current_superuser)],)
@test_router.get("/db_backup", description="Бэкап БД.",)
def db_backup(
    backup_service: DBBackupService = Depends(),
) -> dict[str, int | str]:
    backup_service.check_backup_dir()
    return {
        "app_folder": backup_service.get_base_dir(),
        "time": ANALYTIC_TO_TIME
    }
