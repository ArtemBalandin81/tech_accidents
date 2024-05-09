"""src/api/services/file_attached.py"""
from collections.abc import Sequence

from fastapi import Depends, HTTPException, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.db import get_session
from src.core.db.models import FileAttached, User
from src.core.db.repository.file_attached import FileRepository
from src.core.db.repository.users import UsersRepository
from pathlib import Path
import zipfile
import structlog
import io
from src.api.constants import *
import os

from src.settings import settings


log = structlog.get_logger()


class FileService:
    """Сервис для работы с моделью FileAttached."""

    def __init__(
        self,
        file_repository: FileRepository = Depends(),
        users_repository: UsersRepository = Depends(),
        session: AsyncSession = Depends(get_session)
    ) -> None:
        self._repository: FileRepository = file_repository
        self._users_repository: UsersRepository = users_repository
        self._session: AsyncSession = session

    def check_folder_exists(self, folder: Path) -> None:  # Path - не мб асинхронным?
        """Проверяет наличие каталога, и создает его если нет."""
        if not Path(folder).exists():
            folder.mkdir(parents=True, exist_ok=True)
            log.info("{}".format(DIR_CREATED), folder=folder)

    def rename_validate_file(self, file_timestamp: str, file: UploadFile) -> tuple[str, int]:
        """Переименовывает загружаемый файл под требуемый формат и валидирует его размер и тип."""
        file_name = file_timestamp + "_" + file.filename.lower().translate(TRANSLATION_TABLE)
        file_size = round(file.size / FILE_SIZE_IN, ROUND_FILE_SIZE)
        file_type = file.filename.split(".")[-1]
        if file_type not in settings.FILE_TYPE_DOWNLOAD:
            raise HTTPException(
                status_code=403,
                detail="{}{}{}{}".format(
                    file_name,
                    FILE_TYPE_DOWNLOAD_ALLOWED,
                    ALLOWED_FILE_TYPE_DOWNLOAD,
                    settings.FILE_TYPE_DOWNLOAD
                )
            )
        if file_size > settings.MAX_FILE_SIZE_DOWNLOAD:
            raise HTTPException(
                status_code=403,
                detail="{}{}{}{}{}".format(
                    file_name,
                    FIlE_SIZE_EXCEEDED,
                    file_size,
                    ALLOWED_FILE_SIZE_DOWNLOAD,
                    settings.MAX_FILE_SIZE_DOWNLOAD
                )
            )
        return file_name, file_size

    async def download_files(
            self,
            files: list[UploadFile],
            saved_files_folder: Path,
            file_timestamp: str = FILE_NAME_SAVE_FORMAT
    ) -> list[str] | dict:
        """Загружает файлы в указанный каталог на сервере."""
        download_files_names = []
        self.check_folder_exists(saved_files_folder)
        for file in files:
            file_name_size = self.rename_validate_file(file_timestamp, file)
            try:
                with open(saved_files_folder.joinpath(file_name_size[0]), "wb") as f:
                    f.write(file.file.read())
                download_files_names.append(file_name_size[0])
            except Exception as e:
                return {"message": e.args}
        return download_files_names

    async def write_files_in_db(
            self,
            download_file_names: list[str],
            files_to_write: list[UploadFile],
            user: User,
            file_timestamp: str = FILE_NAME_SAVE_FORMAT
    ) -> list[str]:
        """Записывает в БД переданные файлы."""
        file_names_written_in_db = []
        for file in files_to_write:  # Доп.проверка, что файлы загруженные соответствуют тем, что записываем в БД
            file_name_size = self.rename_validate_file(file_timestamp, file)
            file_name = file_name_size[0]
            file_names_written_in_db.append(file_name)
        if download_file_names != file_names_written_in_db:
            raise HTTPException(
                status_code=409,
                detail="{}{}{}".format(FILES_DOWNLOAD_ERROR, download_file_names, file_names_written_in_db)
            )
        file_names_written_in_db = []
        for file in files_to_write:
            file_name_size = self.rename_validate_file(file_timestamp, file)
            file_name = file_name_size[0]
            file_size = file_name_size[1]
            file_object = {
                "name": file_name,
                "file": bytes("{}{}".format(file_size, FILE_SIZE_VOLUME), FILE_SIZE_ENCODE),
            }
            await self.actualize_object(None, file_object, user)
            file_names_written_in_db.append(file_name)
        return file_names_written_in_db

    async def zip_files(self, files_to_zip: list[Path]) -> Response:
        """Архивирует в zip список переданных файлов."""
        virtual_binary_file = io.BytesIO()  # Open to grab in-memory ZIP contents: virtual binary data file for r & w
        zip_file = zipfile.ZipFile(virtual_binary_file, "w")
        for file_path in files_to_zip:
            file_dir, file_name = os.path.split(file_path)  # Calculate path for file in zip
            zip_file.write(file_path, file_name)  # Add file, at correct path
        zip_file.close()  # Must close zip for all contents to be written
        return Response(
            virtual_binary_file.getvalue(),  # Grab ZIP file from in-memory, make response with correct MIME-type
            media_type="application/x-zip-compressed",
            headers={'Content-Disposition': f'attachment;filename={FILE_NAME_SAVE_FORMAT + "_archive.zip"}'}
        )

    async def actualize_object(  # todo перенести в универсальные сервисы
            self,
            file_id: int | None,
            in_object: dict,
            user: User | int
    ):
        # if in_object["task_start"] > in_object["deadline"]:
        #     raise HTTPException(status_code=422, detail="Check start_time > finish_time")
        # if user is None:  # todo в модели файлов нет пользователей, они появляются через модели задач и простоев
        #     raise HTTPException(status_code=422, detail="Check USER is not NONE!")
        # if type(user) is int:  # Проверяет, что пользователь не передается напрямую id
        #     in_object["user_id"] = user
        # else:
        #     in_object["user_id"] = user.id
        file = FileAttached(**in_object)
        if file_id is None:  # если file_id не передан - создаем, иначе - правим!
            return await self._repository.create(file)
        await self.get(file_id)  # проверяем, что объект для правки существует!
        return await self._repository.update(file_id, file)

    async def get(self, file_id: int) -> FileAttached:
        return await self._repository.get(file_id)

    async def get_all(self) -> Sequence[any]:
        return await self._repository.get_all()

    async def remove(self, file_id: int) -> None:
        file = await self._repository.get(file_id)
        return await self._repository.remove(file)
