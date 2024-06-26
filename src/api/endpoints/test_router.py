"""src/api/endpoints/test_router.py"""
import requests
import structlog
from fastapi import APIRouter, Depends, Query
from src.api.constants import *
from src.api.schemas import DBBackupResponse
from src.core.db.user import current_superuser
from src.services.db_backup import DBBackupService
from src.settings import settings

log = structlog.get_logger()
test_router = APIRouter()


@test_router.get(GET_TEST_URL, description=GET_URL_DESCRIPTION)
def test_get_url(
    url: str = Query(..., example=settings.CONNECTION_TEST_URL_BASE),
) -> dict[str, int | str]:
    status_code = requests.get(url).status_code
    return {url: status_code, "time": ANALYTIC_TO_TIME}


@test_router.get(DB_BACKUP, description=DB_BACKUP_DESCRIPTION, dependencies=[Depends(current_superuser)],)
async def db_backup(
    backup_service: DBBackupService = Depends(),
) -> DBBackupResponse:
    await backup_service.make_copy_db()
    list_of_files_names = await backup_service.get_list_of_names_in_dir()
    total_backups = len(list_of_files_names)
    if total_backups == 0:
        log.aerror("{}".format(DIR_CREATED_ERROR), list_of_files=list_of_files_names, folder=settings.DB_BACKUP_DIR)
        last_backup, first_backup = None, None
    else:
        last_backup = max(list_of_files_names)[0]
        first_backup = min(list_of_files_names)[0]
    return DBBackupResponse(
        total_backups=total_backups,
        last_backup=last_backup,
        first_backup=first_backup,
        time=ANALYTIC_TO_TIME
    )
