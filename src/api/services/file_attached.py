"""src/api/services/file_attached.py"""
import numpy as np

from collections.abc import Sequence

from fastapi import Depends, HTTPException, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.db import get_session
from src.core.db.models import FileAttached, User, TasksFiles
from src.core.db.repository.file_attached import FileRepository
from src.core.db.repository.task import TaskRepository
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
        session: AsyncSession = Depends(get_session),
        task_repository: TaskRepository = Depends(),
        users_repository: UsersRepository = Depends(),
    ) -> None:
        self._repository: FileRepository = file_repository
        self._session: AsyncSession = session
        self._task_repository: TaskRepository = task_repository
        self._users_repository: UsersRepository = users_repository

    async def check_folder_exists(self, folder: Path) -> None:  # Path - не мб асинхронным?
        """Проверяет наличие каталога, и создает его если нет."""
        if not Path(folder).exists():
            folder.mkdir(parents=True, exist_ok=True)
            await log.ainfo("{}".format(DIR_CREATED), folder=folder)

    async def get_all_files_in_folder(self, folder: Path) -> Sequence[str]:
        """Отдает список всех файлов в директории."""
        return [file.name for file in folder.glob('*')]

    async def rename_validate_file(self, file_timestamp: str, file: UploadFile) -> tuple[str, int]:
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
        file_names_downloaded = []
        await self.check_folder_exists(saved_files_folder)
        for file in files:
            file_name_size = await self.rename_validate_file(file_timestamp, file)
            try:
                with open(saved_files_folder.joinpath(file_name_size[0]), "wb") as f:
                    f.write(file.file.read())
                file_names_downloaded.append(file_name_size[0])
            except Exception as e:
                return {"message": e.args}
        await log.ainfo("{}".format(FILES_UPLOADED), files=file_names_downloaded)
        return file_names_downloaded

    async def write_files_in_db(
            self,
            file_names_downloaded: list[str],
            files_to_write: list[UploadFile],
            file_timestamp: str = FILE_NAME_SAVE_FORMAT
    ) -> tuple[list[str], list[int]]:
        """Пишет файлы в БД и проверяет, что загруженные файлы соответствуют тем, что записываются в БД."""
        file_names_written_in_db = []
        for file in files_to_write:
            file_name_size = await self.rename_validate_file(file_timestamp, file)
            file_name = file_name_size[0]
            file_names_written_in_db.append(file_name)
        if file_names_downloaded != file_names_written_in_db:  # todo доп. проверять кол-во файлов до загрузки и после
            raise HTTPException(
                status_code=409,
                detail="{}{}{}".format(FILES_DOWNLOAD_ERROR, file_names_downloaded, file_names_written_in_db)
            )
        file_names_written_in_db = []
        to_create = []
        for file in files_to_write:
            file_name_and_size = await self.rename_validate_file(file_timestamp, file)
            file_name = file_name_and_size[0]
            file_size = file_name_and_size[1]
            file_object = {
                "name": file_name,
                "file": bytes("{}{}".format(file_size, FILE_SIZE_VOLUME), FILE_SIZE_ENCODE),
            }
            file_names_written_in_db.append(file_name)
            to_create.append(FileAttached(**file_object))  # todo лучше схему пайдентик
        await self._repository.create_all(to_create)
        await log.ainfo("{}".format(FILES_WRITTEN_DB), files=to_create)
        return file_names_written_in_db, [obj.id for obj in to_create]  # todo file_names_written_in_db - лишнее

    async def download_and_write_files_in_db(
            self,
            files_to_upload: list[UploadFile],
            saved_files_folder: Path,
            file_timestamp: str = FILE_NAME_SAVE_FORMAT

    ) -> tuple[list[str], list[int]]:
        """Сохраняет файлы, записывает их в БД и отдает их имена и ids."""
        file_names_downloaded = await self.download_files(files_to_upload, saved_files_folder, file_timestamp)
        file_names_and_ids_written_in_db = await self.write_files_in_db(
            file_names_downloaded, files_to_upload, file_timestamp
        )
        await log.ainfo(
            "{}".format(FILES_IDS_WRITTEN_DB),
            names=file_names_and_ids_written_in_db[0],
            ids=file_names_and_ids_written_in_db[1]
        )
        return file_names_and_ids_written_in_db

    async def prepare_files_to_work_with(self, files_attributes: Sequence[int | str], files_dir: Path) -> list[Path]:
        """Отдает список файлов для обработки."""
        if isinstance(files_attributes[0], str):
            return [files_dir.joinpath(file) for file in files_attributes]
        elif isinstance(files_attributes[0], int):
            return [files_dir.joinpath(file_db.name) for file_db in await self.get_by_ids(files_attributes)]
        else:
            await log.aerror("{}{}".format(files_attributes[0], FILE_TYPE_DOWNLOAD_ALLOWED))
            raise HTTPException(status_code=406, detail="{}{}".format(files_attributes[0], FILE_TYPE_DOWNLOAD_ALLOWED))

    async def delete_files_in_folder(self, files_to_delete: Sequence[Path]) -> Sequence[Path]:
        """Удаляет из каталога список переданных файлов."""
        for file in files_to_delete:
            file.unlink()
        return files_to_delete

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

    async def get_arrays_intersection(
            self, array_1: Sequence[str | int], array_2: Sequence[str | int]
    ) -> Sequence[str | int]:
        """Отдает пересечение двух множеств ids."""
        intersection = np.intersect1d(np.array(array_1), np.array(array_2)).tolist()  # noqa
        await log.ainfo("{}{}".format(FILES_IDS_INTERSECTION, intersection))
        return intersection

    async def get_arrays_difference(
            self, array_1: Sequence[str | int], array_2: Sequence[str | int]
    ) -> Sequence[str | int]:
        """Отдает разницу множеств имен или ids: array_1 - array_2."""
        difference = np.setdiff1d(np.array(array_1), np.array(array_2)).tolist()  # noqa
        await log.ainfo("{}{}".format(ARRAYS_DIFFERENCE, difference))
        return np.setdiff1d(np.array(array_1), np.array(array_2)).tolist()  # noqa

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

    async def get_all(self) -> Sequence[FileAttached]:
        return await self._repository.get_all()

    async def get_all_db_file_names_and_ids(self) -> tuple[list[str], list[int]]:
        """Отдает кортеж из имен и их ids всех файлов в БД."""
        db_files = await self._repository.get_all()
        return [db_file.name for db_file in db_files], [db_file.id for db_file in db_files]

    async def get_all_for_search_word(self, search_word: str) -> Sequence[FileAttached]:
        """Отдает файлы, соответствующие критерию поиска."""
        return await self._repository.get_all_for_search_word(search_word)

    async def get_by_ids(self, ids: Sequence[int]) -> Sequence[FileAttached]:
        """Отдает файлы, по их ids."""
        return await self._repository.get_by_ids(ids)

    async def get_all_file_ids_from_tasks(self) -> Sequence[int]:
        """Отдает ids файлов, привязанных ко всем задачам."""
        relations: Sequence[TasksFiles] = await self._repository.get_all_files_from_tasks()
        return [relation.file_id for relation in relations]

    async def get_all_file_names_from_tasks(self) -> Sequence[str]:  # todo если не требуется - удалить
        """Отдает имена файлов, привязанных ко всем задачам."""
        files: Sequence[FileAttached] = await self._task_repository.get_all_files_from_tasks()
        return [file.name for file in files]

    async def remove_files(self, files: Sequence[int], folder: Path) -> Sequence[Path]:
        """Проверяет привязку файлов к задачам, простоям и удаляет их из каталога, но только если они есть в БД."""
        intersection: Sequence[int] = await self.get_arrays_intersection(
            np.array(files), np.array(await self.get_all_file_ids_from_tasks())
        )
        if any(intersection):  # truth value of an array with more than 1 element is ambiguous. Use a.any() or a.all()
            raise HTTPException(status_code=403, detail="{}{}".format(FILES_REMOVE_FORBIDDEN, intersection))
        files_to_remove: Sequence[Path] = await self.prepare_files_to_work_with(files, folder)
        await self.delete_files_in_folder(files_to_remove)
        await self._repository.remove_all(FileAttached, files)
        return files_to_remove
