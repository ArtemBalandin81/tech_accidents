from fastapi import APIRouter

from src.api.endpoints import test_router
from src.settings import settings

api_router = APIRouter(prefix=settings.ROOT_PATH)
api_router.include_router(test_router, prefix="", tags=["Test"])
