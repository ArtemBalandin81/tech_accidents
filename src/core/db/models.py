"""src/core/db/models.py"""
from datetime import date, datetime

from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTable
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import expression, func
from sqlalchemy.sql.sqltypes import BLOB, TIMESTAMP
from src.api.constants import *


class Base(DeclarativeBase):
    """Основа для базового класса."""

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
        onupdate=func.now()
    )
    __name__: Mapped[str]


class Suspension(Base):
    """Модель простоев."""

    __tablename__ = "suspensions"
    risk_accident: Mapped[str] = mapped_column(String(64), nullable=True)  # Risk_Accident model (Many_to_many)  # todo
    description: Mapped[str]  # mapped_column(Text(SUSPENSION_DESCRIPTION_LENGTH))  # next migration if ok todo
    suspension_start: Mapped[datetime] = mapped_column(server_default=func.current_timestamp(), nullable=True)
    suspension_finish: Mapped[datetime] = mapped_column(server_default=func.current_timestamp(), nullable=True)
    tech_process: Mapped[int]
    implementing_measures: Mapped[str]
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))

    files: Mapped[list["FileAttached"]] = relationship(secondary="suspensions_files", back_populates="suspensions")

    def __repr__(self):
        return f"Suspension: {self.id} {self.risk_accident} {self.suspension_start} по {self.suspension_finish}"


class Task(Base):
    """Модель задач: 1 пользователь = 1 задача."""

    __tablename__ = "tasks"
    task: Mapped[str] = mapped_column(String(64), nullable=True)  # String(TASK_NAME_LENGTH), nullable=True)  # todo
    description: Mapped[str]  # mapped_column(Text(TASK_DESCRIPTION_LENGTH)) # # next migration if ok todo
    task_start: Mapped[date] = mapped_column(nullable=True)
    deadline: Mapped[date] = mapped_column(nullable=True)
    tech_process: Mapped[int]
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))  # постановщик (заказчик: внутренний клиент) задачи
    executor_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    is_archived: Mapped[bool] = mapped_column(server_default=expression.false())

    files: Mapped[list["FileAttached"]] = relationship(secondary="tasks_files", back_populates="tasks")

    def __repr__(self):
        return f"Task: {self.id} {self.task} {self.task_start} по {self.deadline}"


class User(SQLAlchemyBaseUserTable[int], Base):
    """Модель пользователя FastAPI Users."""
    pass


class FileAttached(Base):
    """Модель прикрепленных файлов: .png, .jpg., .pdf, .doc, etc"""

    __tablename__ = "files"

    name: Mapped[str] = mapped_column(String(256))  # mapped_column(String(FILE_NAME_LENGTH))  # todo
    file: Mapped[BLOB] = mapped_column(BLOB)
    tasks: Mapped[list["Task"]] = relationship(secondary="tasks_files", back_populates="files")
    suspensions: Mapped[list["Suspension"]] = relationship(secondary="suspensions_files", back_populates="files")

    def __repr__(self):
        return f"<FileAttached {self.name}>"


class TasksFiles(Base):
    """Модель отношений задачи-прикрепленные файлы."""

    __tablename__ = "tasks_files"

    id = None  # means identity through external keys not unique ids
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), primary_key=True)
    file_id: Mapped[int] = mapped_column(ForeignKey("files.id"), primary_key=True)

    def __repr__(self):
        return f"<Task {self.task_id} - Files {self.file_id}>"


class SuspensionFiles(Base):
    """Модель отношений простои-прикрепленные файлы."""

    __tablename__ = "suspensions_files"

    id = None  # means identity through external keys not unique ids
    suspension_id: Mapped[int] = mapped_column(ForeignKey("suspensions.id"), primary_key=True)
    file_id: Mapped[int] = mapped_column(ForeignKey("files.id"), primary_key=True)

    def __repr__(self):
        return f"<Suspension {self.suspension_id} - Files {self.file_id}>"
