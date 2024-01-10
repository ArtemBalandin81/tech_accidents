"""src/application.py"""
import asyncio

from datetime import datetime
from fastapi import FastAPI
from src.api.router import api_router

from src.settings import settings
from src.services.register_connection_errors import ConnectionErrorService
from src.services.db_backup import DBBackupService

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_TITLE,
        description=settings.APP_DESCRIPTION
    )
    app.include_router(api_router)

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
