import sys
from functools import wraps

from src.settings import settings

TASK_DEADLINE_FORMAT = "%d.%m.%y"


def auto_commit(func):
    @wraps(func)
    async def auto_commit_wraps(self, *args, commit=True):
        result = await func(self, *args)
        if commit:
            await self._session.commit()
        return result

    return auto_commit_wraps
