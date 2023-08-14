from .suspensions import suspension_router
from .test_router import test_router
from .user import router as user_router

__all__ = (
    "suspension_router",
    "test_router",
    "user_router",
)
