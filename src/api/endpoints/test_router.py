"""src/api/endpoints/test_router.py"""
import requests

from fastapi import APIRouter, Query, Depends

from src.api.constants import ANALYTIC_TO_TIME
from src.api.schemas import DBBackupResponse
from src.core.db.user import current_superuser
from src.services.db_backup import DBBackupService

test_router = APIRouter()

@test_router.get("/test_get_url", description="Проверка доступа к сайту.")
def test_get_url(
    url: str = Query(..., example="https://www.agidel-am.ru"),
) -> dict[str, int | str]:
    status_code = requests.get(url).status_code
    return {url: status_code, "time": ANALYTIC_TO_TIME}


@test_router.get("/db_backup", description="Бэкап БД.", dependencies=[Depends(current_superuser)],)
def db_backup(
    backup_service: DBBackupService = Depends(),
) -> DBBackupResponse:
    backup_service.make_copy_db()
    list_of_files_names = backup_service.get_list_of_names_in_dir()
    return DBBackupResponse(
        total_backups=len(list_of_files_names),
        last_backup=max(list_of_files_names)[0],
        first_backup=min(list_of_files_names)[0],
        time=ANALYTIC_TO_TIME
    )
