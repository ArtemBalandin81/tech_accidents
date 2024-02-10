"""src/application.py"""
import asyncio

from asgi_correlation_id import CorrelationIdMiddleware
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.logging.middleware import LoggingMiddleware
from src.core.logging.setup import setup_logging
from src.settings import settings
from src.services.register_connection_errors import ConnectionErrorService
from src.services.db_backup import DBBackupService


def include_router(app: FastAPI):
    from src.api.router import api_router

    app.include_router(api_router)


def add_middleware(app: FastAPI):  #todo логгируется только сервер, но не мои инфо - разобраться как так-то!!!
    origins = ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    setup_logging()
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(CorrelationIdMiddleware)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_TITLE,
        description=settings.APP_DESCRIPTION
    )
    include_router(app)
    add_middleware(app)  # логгирование

    @app.on_event("startup")
    async def startup_event():
        """Действия при запуске сервера."""
        print("Server started :", datetime.now())  # TODO заменить логированием
        asyncio.create_task(ConnectionErrorService().run_check_connection())
        asyncio.create_task(DBBackupService().run_db_backup()) if settings.DB_BACKUP else None

    @app.on_event("shutdown")
    async def shutdown_event():
        """Действия после остановки сервера."""
        print('Server shutdown :', datetime.now())  # TODO заменить логированием

    return app
