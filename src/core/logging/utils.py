"""src/core/logging/utils.py"""
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import ParamSpec, TypeVar

import structlog
from src.api.constants import FUNCTION_STARTS, MISS_LOGGING_UPDATES

ReturnType = TypeVar("ReturnType")
ParameterTypes = ParamSpec("ParameterTypes")

log = structlog.get_logger().bind(file_name=__file__)


async def logging_updates(*args, **kwargs):
    await log.ainfo(MISS_LOGGING_UPDATES, args=args, kwargs=kwargs)


def logger_decor(
    coroutine: Callable[ParameterTypes, Awaitable[ReturnType]]
) -> Callable[ParameterTypes, Awaitable[ReturnType]]:
    @wraps(coroutine)
    async def wrapper(*args: ParameterTypes.args, **kwargs: ParameterTypes.kwargs) -> ReturnType:
        await log.ainfo("{}{}".format(FUNCTION_STARTS, coroutine.__name__), args=args, kwargs=kwargs)
        return await coroutine(*args, **kwargs)

    return wrapper
