"""src/api/validators.py"""

from collections.abc import Sequence
from datetime import date
from typing import TypeVar

import structlog
from fastapi import HTTPException, UploadFile
from pydantic import PositiveInt
from src.api.constants import *
from src.core.db.models import User

DatabaseModel = TypeVar("DatabaseModel")
log = structlog.get_logger()


async def check_author_or_super_user(
        user: User,
        instance: DatabaseModel,
) -> None:
    """Проверяет пользователя на авторство, или наличие прав админа."""
    if user.id != instance.user_id and not user.is_superuser:
        details = "{}".format(ONLY_AUTHOR)
        await log.aerror(ONLY_AUTHOR, author=instance.user_id, current_user=user.id, is_super_user=user.is_superuser)
        raise HTTPException(status_code=403, detail=details)


async def check_start_not_exceeds_finish(
        start_process: str | datetime | date,
        finish_process: str | datetime | date,
        format_datetime: str
) -> None:
    """Проверяет вводимые значения на соответствие формату datetime, а начало периода задано не позднее его конца."""
    if isinstance(start_process, str):
        try:
            start_process: datetime = datetime.strptime(start_process, format_datetime)
        except ValueError as e:
            details = "{}{}{}".format(NOT_DATETIME_FORMAT, ANALYTICS_START, start_process)
            await log.aerror(details, start_process=start_process, format=format_datetime, error=e)
            raise HTTPException(status_code=422, detail=details)
    if isinstance(finish_process, str):
        try:
            finish_process: datetime = datetime.strptime(finish_process, format_datetime)
        except ValueError as e:
            details = "{}{}{}".format(NOT_DATETIME_FORMAT, ANALYTICS_FINISH, finish_process)
            await log.aerror(details, finish_process=finish_process, format=format_datetime, error=e)
            raise HTTPException(status_code=422, detail=details)
    if start_process is None or finish_process is None:
        return
    if start_process > finish_process:
        await log.aerror(START_FINISH_TIME, start_process=start_process, finish_process=finish_process)
        raise HTTPException(
            status_code=422, detail="{}{}{}{}{}".format(START_FINISH_TIME, SPACE, start_process, SPACE, finish_process)
        )


async def check_same_files_not_to_download(files_to_upload: list[UploadFile]) -> None:
    """Проверяет, что один и тот же файл не загружается дважды."""
    file_names = [file.filename for file in files_to_upload]
    if len(set(file_names)) != len(file_names):
        await log.aerror(FILES_DOWNLOAD_ERROR, detail=SAME_NAMES, file_names=file_names)
        raise HTTPException(status_code=403, detail="{}{}{}".format(FILES_DOWNLOAD_ERROR, SAME_NAMES, file_names))


async def check_not_download_and_delete_files_at_one_time(
        to_unlink_files: bool,
        file_to_upload: UploadFile | None
) -> None:
    """Проверяет, что одновременно не выбрана опция загрузки и удаления файлов."""
    if to_unlink_files and file_to_upload is not None:
        await log.aerror("{}".format(TASKS_FILES_REMOVE_AND_SET))
        raise HTTPException(status_code=406, detail="{}".format(TASKS_FILES_REMOVE_AND_SET))


async def check_exist_files_attached(
        file_ids: Sequence[PositiveInt],
        task_id: PositiveInt
) -> None:
    """Проверяет, что прикрепленные к модели файлы существуют."""
    if not file_ids:
        details = "{}{}{}{}{}".format(TASK, task_id, FILES_ATTACHED_TO_TASK, file_ids, NOT_FOUND)
        await log.aerror(details, task_id=task_id, files_ids=file_ids)
        raise HTTPException(status_code=404, detail=details)
