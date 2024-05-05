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
import io
from src.api.constants import FILE_NAME_SAVE_FORMAT, TRANSLATION_TABLE
import os


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

    # todo проверять тип загружаемого файла: только (".doc", ".docx", ".xls", ".xlsx", ".img", ".png", ".txt", ".pdf", ".jpeg")
    # todo проверять размер загружаемого файла: не более 10 МБ
    async def download_files(self, files: list[UploadFile], saved_files_folder: Path) -> None | dict:
        """Загружает файлы в указанный каталог на сервере."""
        for file in files:
            file_name = FILE_NAME_SAVE_FORMAT + "_" + file.filename.lower().translate(TRANSLATION_TABLE)
            try:
                with open(saved_files_folder.joinpath(file_name), "wb") as f:  # todo проверять что есть, иначе - создавать директорию
                    f.write(file.file.read())
            except Exception as e:
                return {"message": e.args}

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

    async def write_files_in_db(self, files_to_write: list[UploadFile], user: User) -> None:
        """Записывает в БД переданные файлы."""
        for file in files_to_write:
            file_name = FILE_NAME_SAVE_FORMAT + "_" + file.filename.lower().translate(TRANSLATION_TABLE)
            file_object = {
                "name": file_name,
                "file": bytes(file.filename + "---" + str(round(file.size/1000000, 2)), 'utf-8'),  # todo сделай красиво
            }
            await self.actualize_object(None, file_object, user)

    # async def change_schema_response(
    #         self,
    #         file_attached: FileAttached,
    # ) -> dict:
    #     """Изменяет и добавляет поля в словарь в целях наглядного представления в ответе api."""
    #     user = await self._users_repository.get(task.user_id)
    #     executor = await self._users_repository.get(task.executor)  # todo поменять на executor_id
    #     task_to_dict = task.__dict__
    #     task_to_dict["user_email"] = user.email
    #     task_to_dict["executor_email"] = executor.email
    #     task_to_dict["business_process"] = TechProcess(str(task.tech_process)).name  # str требуется enum-классу
    #     return task_to_dict

    # async def perform_changed_schema(  # todo сделать универсальный сервис под разные модели и перенести в base
    #         self,
    #         tasks: Task | Sequence[Task],
    # ) -> Sequence[dict]:
    #     """Готовит список словарей для отправки в api."""
    #     list_changed_response = []
    #     if type(tasks) is not list:  # todo use isinstance() instead of type()
    #         list_changed_response.append(await self.change_schema_response(tasks))
    #     else:
    #         for task in tasks:
    #             list_changed_response.append(await self.change_schema_response(task))
    #     return list_changed_response

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
