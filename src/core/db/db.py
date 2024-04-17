"""src/core/db/db.py"""
from typing import Generator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from src.settings import settings


engine = create_async_engine(settings.DATABASE_URL, echo=False)  # echo=True см. SQL-запросы в консоли
# connect_args={"check_same_thread": False} - только для SQLlite
# connect_args для create_async_engine не нужен!!!

async def get_session() -> Generator[AsyncSession, None, None]:
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        yield session
