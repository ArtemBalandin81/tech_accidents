"""src/core/db/models.py"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import ForeignKey, String, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.sql.sqltypes import TIMESTAMP
from sqlalchemy.sql.expression import text

from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTable

from src.api.constants import TZINFO


class Base(DeclarativeBase):
    """Основа для базового класса."""

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        #DateTime(timezone=True),
        TIMESTAMP(timezone=True),  # локально дает создавать, а в доккер - нет
        #server_default=text('now'),
        server_default=func.current_timestamp(),  # локально дает создавать, а в доккер - нет
        #server_default=func.now(TZINFO),
        #default=func.now() + timedelta(hours=settings.TIMEZONE_OFFSET),
    )
    #  Column(Datetime, lambda: default=datetime.datetime.now(datetime.timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        #DateTime(timezone=True),
        TIMESTAMP(timezone=True),
        #server_default=text('now'),
        server_default=func.current_timestamp(),
        #server_default=func.now(TZINFO),
        #default=func.now() + timedelta(hours=settings.TIMEZONE_OFFSET),
        onupdate=func.current_timestamp(),
    )
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


class User(SQLAlchemyBaseUserTable[int], Base):
    """Модель пользователя FastAPI Users."""
    pass
