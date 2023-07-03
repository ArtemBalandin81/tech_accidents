from fastapi import FastAPI
from src.api.router import api_router
from src.settings import settings

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_title,
        description=settings.app_description
    )
    app.include_router(api_router)

    return app
