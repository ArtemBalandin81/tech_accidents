"""src/core/db/repository/file_attached.py"""
from collections.abc import Sequence

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.db.db import get_session
from src.core.db.models import FileAttached
from src.core.db.repository.base import ContentRepository


class FileRepository(ContentRepository):
    """Репозиторий для работы с моделью FileAttached."""

    def __init__(self, session: AsyncSession = Depends(get_session)) -> None:
        super().__init__(session, FileAttached)
