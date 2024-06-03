"""Определяет порядок эндпоинтов: src/api/router.py"""

from fastapi import APIRouter
from src.api.endpoints import file_router, suspension_router, task_router, test_router, user_router
from src.settings import settings

api_router = APIRouter(prefix=settings.ROOT_PATH)
api_router.include_router(suspension_router, prefix="/suspensions")
api_router.include_router(task_router, prefix="/tasks")
api_router.include_router(file_router, prefix="/files")
api_router.include_router(test_router, prefix="/services", tags=["services"])
api_router.include_router(user_router)
