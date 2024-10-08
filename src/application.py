"""src/application.py"""
import asyncio
from datetime import datetime

import structlog
from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.logging.middleware import LoggingMiddleware
from src.core.logging.setup import setup_logging
from src.core.logging.utils import logger_decor
from src.services.db_backup import DBBackupService
from src.services.register_connection_errors import ConnectionErrorService
from src.settings import settings

log = structlog.get_logger().bind(file_name=__file__)


def include_router(app: FastAPI):
    from src.api.router import api_router

    app.include_router(api_router)


def add_middleware(app: FastAPI):
    origins = ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    setup_logging()  # Procharity example of pytest settings
    app.add_middleware(LoggingMiddleware)  # creates api logs
    app.add_middleware(CorrelationIdMiddleware)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_TITLE,
        description=settings.APP_DESCRIPTION
    )
    include_router(app)
    add_middleware(app)

    @app.on_event("startup")
    @logger_decor
    async def startup_event():
        """Действия при запуске сервера."""
        await log.ainfo("Server_started", time=str(datetime.now()))
        asyncio.create_task(ConnectionErrorService().run_check_connection())
        asyncio.create_task(DBBackupService().run_db_backup()) if settings.DB_BACKUP else None

    @app.on_event("shutdown")
    @logger_decor
    async def shutdown_event():
        """Действия после остановки сервера."""
        await log.ainfo("Server_shutdown", time=str(datetime.now()))

    return app
