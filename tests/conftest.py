"""Конфигурационный файл для тестов: tests/conftest.py"""

import asyncio
import os
import sys
from typing import Any, Generator

import pytest
import structlog
from fastapi import FastAPI
from httpx import AsyncClient
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

#this is to include backend dir in sys.path so that we can import from db,main.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.router import api_router
from src.core.db.db import get_session
from src.core.db.models import (Base, FileAttached, Suspension,
                                SuspensionsFiles, Task, TasksFiles, User)
from src.settings import settings

log = structlog.get_logger().bind(file_name=__file__)

def start_application():
    app = FastAPI()
    app.include_router(api_router)
    return app

@pytest.fixture(scope='session')
def anyio_backend():
    """Use only 'asyncio' and disable 'trio' tests: https://anyio.readthedocs.io/en/stable/testing.html."""
    return 'asyncio'



engine = create_async_engine(settings.DATABASE_URL_TEST, echo=settings.ECHO_TEST_DB)

@pytest.fixture(scope='session')
async def async_db_engine():
    """Create a fresh database on each test case."""
    async with engine.begin() as conn:
        # Здесь все операции c БД выполняются в рамках одной транзакции, которая либо фиксируется успешно
        # после выполнения всего кода, либо откатывается в случае возникновения исключения:
        # await conn.run_sync(Base.metadata.drop_all)
        # await conn.run_sync(Base.metadata.create_all)
        # Создание объектов модели и их сохранение
        # await session.add(user)
        # await session.commit()
        await conn.run_sync(Base.metadata.create_all)
        # super_user = User(email="test_super_user@nofoobar.com", hashed_password="super_testing", is_superuser=True)
        # await conn.add(super_user)
        # await conn.commit()
        # super_user_db = await conn.refresh(super_user)
        # await log.ainfo("super_user_created:", super_user_db=super_user_db)


    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)  # drop all database every time when test complete


# truncate all table to isolate tests
@pytest.fixture(scope='function')
async def async_db(async_db_engine):
    async_session = sessionmaker(
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
        bind=async_db_engine,
        class_=AsyncSession,
    )

    async with async_session() as session:
        await session.begin()

        yield session

        await session.rollback()

        # Error sqlalchemy.exc.ArgumentError: Textual SQL expression  todo
        #  'TRUNCATE tasks_files CASC...' should be explicitly declared as text('TRUNCATE tasks_files CASC...')
        # for table in reversed(Base.metadata.sorted_tables):
        #     await session.execute(f'TRUNCATE {table.name} CASCADE;')
        #     await session.commit()


@pytest.fixture(scope="function")
def app() -> Generator[FastAPI, Any, None]:
    """Start app"""
    # Base.metadata.create_all(engine)  # Create the tables.  # ??? todo
    _app = start_application()
    yield _app
    # Base.metadata.drop_all(engine)  # ??? todo


@pytest.fixture(scope="function")
async def async_client(app, async_db: AsyncSession) -> AsyncClient:
    """
    Create a new FastAPI AsyncClient that uses the `async_db` fixture to override
    the `get_session` dependency that is injected into routes.
    """

    def _get_test_db():
        """Utility function to wrap the database session in a generator.

        Yields:
            Iterator[AsyncSession]: An iterator containing one database session.
        """
        try:
            yield async_db
        finally:
            pass

    app.dependency_overrides[get_session] = _get_test_db
    return AsyncClient(app=app, base_url="http://testserver")


# let test session to know it is running inside event loop  # todo maybe is not necessary to delete
@pytest.fixture(scope='session')
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def super_user_orm(async_db: AsyncSession) -> User:
    """Create super_user in database"""
    email = "super_user_fixture@f.com"
    password = "testings"
    pwd_context = CryptContext(schemes=["bcrypt"])  # hash password
    super_user = User(email=email, hashed_password=pwd_context.hash(password), is_superuser=True)
    async_db.add(super_user)
    await async_db.commit()
    await async_db.refresh(super_user)
    await log.ainfo("super_user_orm_created:", super_user_orm=super_user)
    return super_user

@pytest.fixture
async def user_orm(async_db: AsyncSession) -> User:
    """Create user in database"""
    email = "user_fixture@f.com"
    password = "testings"
    pwd_context = CryptContext(schemes=["bcrypt"])  # hash password
    user = User(email=email, hashed_password=pwd_context.hash(password), is_superuser=False)
    async_db.add(user)
    await async_db.commit()
    await async_db.refresh(user)
    await log.ainfo("user_orm_created:", user_orm=user)
    return user
