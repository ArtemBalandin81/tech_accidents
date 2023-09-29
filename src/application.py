"""src/application.py"""
from datetime import datetime
from fastapi import FastAPI
from src.api.router import api_router
from src.settings import settings

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_TITLE,
        description=settings.APP_DESCRIPTION
    )
    app.include_router(api_router)

    @app.on_event("startup")
    async def startup_event():
        """Действия при запуске сервера."""
        print('Server started :', datetime.now())

    @app.on_event("shutdown")
    async def shutdown_event():
        """Действия после остановки сервера."""
        print('Server shutdown :', datetime.now())


    return app
