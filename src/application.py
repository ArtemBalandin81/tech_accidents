"""src/application.py"""
import asyncio

from datetime import datetime
from fastapi import FastAPI
from src.api.router import api_router
from src.settings import settings
from src.services.test_connection import run_test_connection_asyncio

CONNECTION_TEST_URL: str = "https://www.agidel-am.ru"


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_TITLE,
        description=settings.APP_DESCRIPTION
    )
    app.include_router(api_router)

    @app.on_event("startup")
    async def startup_event():
        """Действия при запуске сервера."""
        print("Server started :", datetime.now())
        asyncio.create_task(run_test_connection_asyncio())

    @app.on_event("shutdown")
    async def shutdown_event():
        """Действия после остановки сервера."""
        print('Server shutdown :', datetime.now())

    return app
