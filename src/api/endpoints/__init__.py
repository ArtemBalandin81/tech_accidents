from .files_attached import file_router
from .suspensions import suspension_router
from .tasks import task_router
from .service_router import service_router
from .user import router as user_router

__all__ = (
    "file_router",
    "suspension_router",
    "task_router",
    "service_router",
    "user_router",
)
