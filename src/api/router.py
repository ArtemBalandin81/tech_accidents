from fastapi import APIRouter

from src.api.endpoints import suspension_router, test_router, user_router
from src.settings import settings

api_router = APIRouter(prefix=settings.ROOT_PATH)
api_router.include_router(suspension_router, prefix="/suspensions", tags=["Suspensions"])
api_router.include_router(test_router, prefix="", tags=["Test"])
api_router.include_router(user_router)
