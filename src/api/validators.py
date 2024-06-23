"""src/api/validators.py"""

from datetime import date

import structlog
from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.constants import *

log = structlog.get_logger()


async def check_start_not_exceeds_finish(
        start_process: str | datetime | date,
        finish_process: str | datetime | date,
        format_datetime: str
) -> None:
    """Проверяет, что начало процесса задано не позднее его окончания."""
    if isinstance(start_process, str):
        start_process: datetime = datetime.strptime(start_process, format_datetime)
    if isinstance(finish_process, str):
        finish_process: datetime = datetime.strptime(finish_process, format_datetime)
    if start_process > finish_process:
        await log.aerror(START_FINISH_TIME, start_process=start_process, finish_process=finish_process)
        raise HTTPException(
            status_code=422, detail="{}{}{}{}".format(START_FINISH_TIME, start_process, SPACE, finish_process)
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


# todo delete

# async def check_name_duplicate(
#         room_name: str,
#         session: AsyncSession,
# ) -> None:
#     room_id = await meeting_room_crud.get_room_id_by_name(room_name, session)
#     if room_id is not None:
#         raise HTTPException(
#             status_code=422,
#             detail='Переговорка с таким именем уже существует!',
#         )


# async def check_meeting_room_exists(
#         meeting_room_id: int,
#         session: AsyncSession,
# ) -> MeetingRoom:
#     meeting_room = await meeting_room_crud.get(meeting_room_id, session)
#     if meeting_room is None:
#         raise HTTPException(
#             status_code=404,
#             detail='Переговорка не найдена!'
#         )
#     return meeting_room
#
#
# async def check_reservation_intersections(
#         **kwargs,
# ) -> None:
#     reservations = await reservation_crud.get_reservations_at_the_same_time(
#         **kwargs
#     )
#     if reservations:
#         raise HTTPException(
#             status_code=422,
#             detail=str(reservations),
#         )
#
# async def check_reservation_before_edit(
#         reservation_id: int,
#         session: AsyncSession,
#         user: User,
# ) -> Reservation:
#     reservation = await reservation_crud.get(
#         # Для понятности кода можно передавать аргументы по ключу.
#         obj_id=reservation_id,
#         session=session
#     )
#     if not reservation:
#         raise HTTPException(status_code=404, detail='Бронь не найдена!')
#     if reservation.user_id != user.id and not user.is_superuser:
#         raise HTTPException(
#             status_code=403,
#             detail='Невозможно редактировать или удалить чужую бронь!'
#         )
#     return reservation

