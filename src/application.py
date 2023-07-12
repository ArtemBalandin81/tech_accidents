from fastapi import FastAPI
from src.api.router import api_router
from src.settings import settings

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_TITLE,
        description=settings.APP_DESCRIPTION
    )
    app.include_router(api_router)

    return app
