"""Конфигурационный файл для тестов: tests/conftest.py"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Generator, Sequence, TypeVar

import pytest
import structlog
from fastapi import FastAPI
from httpx import AsyncClient
from passlib.context import CryptContext
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# this is to include backend dir in sys.path so that we can import from db,main.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.api.constants import *
from src.api.router import api_router
from src.core.db.db import get_session
from src.core.db.models import Base, FileAttached, Suspension, Task, User
from src.core.logging.setup import setup_logging
from src.settings import settings

setup_logging()  # Procharity example of pytest settings (comment this for standard logging)

log = structlog.get_logger() if settings.FILE_NAME_IN_LOG is False else structlog.get_logger().bind(file_name=__file__)
DatabaseModel = TypeVar("DatabaseModel")
CONFTEST_ROUTES_DIR = Path(__file__).resolve().parent
TEST_ROUTES_DIR = CONFTEST_ROUTES_DIR.joinpath("test_routes")


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
    """Create connection to database."""
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
    """Create super_user in database."""
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
    """Create user in database."""
    email = "user_fixture@f.com"
    password = "testings"
    pwd_context = CryptContext(schemes=["bcrypt"])  # hash password
    user = User(email=email, hashed_password=pwd_context.hash(password), is_superuser=False)
    async_db.add(user)
    await async_db.commit()
    await async_db.refresh(user)
    await log.ainfo("user_orm_created:", user_orm=user)
    return user


@pytest.fixture
async def user_from_settings(async_db: AsyncSession) -> User:
    """Create user_from_settings in database in order to satisfy ENUM STAFF validations in api."""
    user_settings_email = json.loads(settings.STAFF)['1']
    password = "testings"
    pwd_context = CryptContext(schemes=["bcrypt"])  # hash password
    user = User(email=user_settings_email, hashed_password=pwd_context.hash(password), is_superuser=False)
    async_db.add(user)
    await async_db.commit()
    await async_db.refresh(user)
    await log.ainfo("user_from_settings_created:", email=user.email, id=user.id)
    return user


@pytest.fixture
async def suspensions_orm(async_db: AsyncSession, user_from_settings: User, user_orm: User) -> Sequence[Suspension]:
    """
    Create a suspension in database by user from settings and by test user from orm.
    for testing intervals: starts = (now - 1 day), finish = now
    """
    now = datetime.now()
    scenarios = (
        # description, suspension_start, suspension_finish, measures, user_id:
        ("_1_[]", now - timedelta(days=2), now - timedelta(days=1, hours=23, minutes=59), "1", user_from_settings.id),
        ("_[2875_]", now - timedelta(days=2), now - timedelta(minutes=5), "2", user_orm.id),
        ("[_10_]", now - timedelta(minutes=15), now - timedelta(minutes=5), "3", user_from_settings.id),
        ("[_60]_", now - timedelta(minutes=30), datetime.now() + timedelta(minutes=30), "4", user_orm.id)
    )
    suspensions_list = []
    for description, suspension_start, suspension_finish, measures, user_id in scenarios:
        suspension = Suspension(
            risk_accident=next(iter(json.loads(settings.RISK_SOURCE).values())),  # the first item in dictionary
            description=description,
            suspension_start=suspension_start,  # CREATE_SUSPENSION_FROM_TIME,
            suspension_finish=suspension_finish,  # CREATE_SUSPENSION_TO_TIME,
            tech_process=next(iter(json.loads(settings.TECH_PROCESS).values())),  # :int = 25 -first item in dictionary
            implementing_measures=measures,
            user_id=user_id
        )
        suspensions_list.append(suspension)
    async_db.add_all(suspensions_list)
    await async_db.commit()
    # await async_db.refresh(suspensions_list)
    await log.ainfo("suspensions_orm_created:", suspensions_orm=suspensions_list)
    return suspensions_list


async def remove_all(async_db, instance: DatabaseModel, instances: Sequence[int] | None = None) -> Sequence[int]:
    """Remove data in database and return the result in ids."""
    if instances is not None:
        await async_db.execute(delete(instance).where(instance.id.in_(instances)))
    else:
        await async_db.execute(delete(instance))  # delete all users to clean the database and isolate tests
    await async_db.commit()
    cleaned_item = await async_db.scalars(select(instance))
    return [cleaned_item.id for cleaned_item in cleaned_item.all()]


async def clean_test_database(async_db, *args) -> structlog:
    """Clean all model data in database and return the result in logs."""
    clean_log_dict = {}
    for arg in args:
        ids_after_remove = await remove_all(async_db, arg)
        model_name = arg.__tablename__
        details = f"{model_name} ids: {ids_after_remove}"
        assert ids_after_remove == [], f"ids of {model_name} haven't been deleted. {details}"
        clean_log_dict[model_name] = ids_after_remove
    await log.ainfo("Clean_test_database_and_files_folder", info=clean_log_dict)


async def get_file_names_for_model_db(async_db, instance: DatabaseModel, instance_id: int) -> Sequence[FileAttached]:
    """Get list of file names attached to a Model."""
    objects = await async_db.scalars(
        select(FileAttached)
        .join(instance.files)
        .where(instance.id == instance_id)
    )
    files = objects.all()
    return [file.name for file in files]


async def delete_files_in_folder(files_to_delete: Sequence[Path]) -> Sequence[Path] | dict[str, tuple[Any, ...]]:
    """Удаляет из каталога список переданных файлов (физическое удаление файлов)."""
    for file in files_to_delete:
        try:
            file.unlink()
        except FileNotFoundError as e:
            details = "{}{}{}".format(FILES_IN_FOLDER, NOT_FOUND, e.args)
            await log.aerror(details, file_to_remove=file)
            # raise HTTPException(status_code=403, detail=details)
            # return {"message": e.args}  # files in folder will not be deleted cause of exception return
    await log.ainfo("Delete_files_in_folder", deleted=files_to_delete)
    return files_to_delete


async def create_test_files(test_files: list[str] = ("testfile.txt", "testfile2.txt", "testfile3.txt")) -> None:
    """Создает в каталоге тестовые файлы для загрузки, если их нет."""
    for file_name in test_files:
        if not os.path.exists(TEST_ROUTES_DIR.joinpath(file_name)):
            with open(TEST_ROUTES_DIR.joinpath(file_name), "w") as file:
                file.write(f"{file_name} has been created: {datetime.now(TZINFO).strftime(DATE_TIME_FORMAT)}")
