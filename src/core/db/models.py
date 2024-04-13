"""src/core/db/models.py"""
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func, expression
from sqlalchemy.sql.sqltypes import TIMESTAMP

from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTable


class Base(DeclarativeBase):  # todo без применения миграций не работают изменения
    """Основа для базового класса."""

    id: Mapped[int] = mapped_column(primary_key=True)
    # created_at = Column(DateTime, server_default=func.current_timestamp())
    # updated_at = Column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.now())


    # created_at: Mapped[datetime] = mapped_column(  # todo [SQL: ALTER TABLE suspensions ALTER COLUMN created_at TYPE DATETIME]
    #     TIMESTAMP(timezone=True),  # error: ALTER COLUMN created_at TYPE TIMESTAMP
    #     # DateTime(timezone=True),  # error: ALTER COLUMN created_at TYPE DATETIME
    #     # nullable=True,  # error: ALTER COLUMN created_at DROP NOT NULL
    #     default=func.current_timestamp(),  # table_with_timestamp_from_python
    #     # server_default=func.current_timestamp()  # todo: if table_with_timestamp_from_db, or:
    #     # server_default=func.utc_thing(func.current_timestamp()),
    # )
    # updated_at: Mapped[datetime] = mapped_column(
    #     TIMESTAMP(timezone=True),  # error: ALTER COLUMN created_at TYPE TIMESTAMP
    #     # DateTime(timezone=True),  # error: ALTER COLUMN created_at TYPE DATETIME
    #     # nullable=True,  # так было в cat_charity_fund
    #     default=func.current_timestamp(),  # table_with_timestamp_from_python
    #     onupdate=func.now(),
    #     # server_default=func.current_timestamp(),  # todo: if table_with_timestamp_from_db
    #     # server_default=func.utc_thing(func.current_timestamp()),
    #     # server_default=func.now()+timedelta(hours=5),
    # )
    __name__: Mapped[str]


class Suspension(Base):
    """Модель простоев."""

    __tablename__ = "suspensions"
    risk_accident: Mapped[str] = mapped_column(String(64), nullable=True)  # TODO Risk_Accident model (Many_to_many)
    description: Mapped[str]
    datetime_start: Mapped[datetime] = mapped_column(server_default=func.current_timestamp(), nullable=True)
    datetime_finish: Mapped[datetime] = mapped_column(server_default=func.current_timestamp(), nullable=True)
    tech_process: Mapped[int]
    implementing_measures: Mapped[str]
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))

    def __repr__(self):
        return f"Suspension: {self.id} {self.risk_accident} {self.datetime_start} по {self.datetime_finish}"


class Task(Base):
    """Модель задач: 1 пользователь = 1 задача."""

    __tablename__ = "tasks"
    task: Mapped[str] = mapped_column(String(64), nullable=True)
    description: Mapped[str]
    task_start: Mapped[date] = mapped_column(nullable=True)
    deadline: Mapped[date] = mapped_column(nullable=True)
    tech_process: Mapped[int]
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))  # постановщик (заказчик: внутренний клиент) задачи
    executor: Mapped[int] = mapped_column(ForeignKey("user.id"))  # исполнитель # todo заменить на executor_id
    is_archived: Mapped[bool] = mapped_column(server_default=expression.false())

    def __repr__(self):
        return f"Task: {self.id} {self.task} {self.task_start} по {self.deadline}"


class User(SQLAlchemyBaseUserTable[int], Base):
    """Модель пользователя FastAPI Users."""
    pass
