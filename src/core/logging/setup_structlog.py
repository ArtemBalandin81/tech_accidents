"""
Альтернативная настройка structlog - для тестирования основной настройки
src/core/logging/setup_structlog.py
simple structlog setup from:
https://www.angelospanag.me/blog/structured-logging-using-structlog-and-fastapi
"""
import logging
import logging.config
import os
import sys
from pathlib import Path

import structlog
import ujson
from src.settings import settings
from structlog.types import EventDict, Processor

os.makedirs(settings.LOG_DIR, exist_ok=True)


def drop_color_message_key(_, __, event_dict: EventDict) -> EventDict:
    """
    Uvicorn logs the message a second time in the extra `color_message`, but we don't
    need it. This processor drops the key from the event dict if it exists.
    """
    event_dict.pop("color_message", None)
    return event_dict


def _get_renderer() -> structlog.processors.JSONRenderer | structlog.dev.ConsoleRenderer:
    """Получаем рендерер на основании параметров среды: возвращаем рендерер structlog."""
    if settings.JSON_LOGS is False:
        return structlog.dev.ConsoleRenderer()
    return structlog.processors.JSONRenderer(
        indent=2,
        sort_keys=True,
        serializer=ujson.dumps,
        ensure_ascii=False,
    )

def setup_structlog():
    """Основные настройки логирования."""
    # structlog.reset_defaults()  # need to test it
    _log_dir: Path = Path(os.path.join(settings.LOG_DIR, settings.LOG_FILE))
    log = structlog.get_logger()

    # Disable uvicorn logging
    # logging.getLogger("uvicorn.error").disabled = True
    # logging.getLogger("uvicorn.access").disabled = True

    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,  # merge contextvars: requests, time, user etc.
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),  # allow adding extra positioning log info
        structlog.stdlib.ExtraAdder(),
        drop_color_message_key,
        structlog.processors.TimeStamper(fmt="iso", utc=False),
        structlog.processors.StackInfoRenderer(),
    ]

    # Structlog configuration custom manual
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=settings.LOG_LEVEL)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.PositionalArgumentsFormatter(),  # allow adding extra positioning log info
            # structlog.stdlib.ExtraAdder(),
            structlog.stdlib.add_log_level,
            # structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),  # Could be an error!!!
            structlog.processors.TimeStamper(fmt="iso", utc=False),
            structlog.processors.dict_tracebacks,  # To add info about all the exceptions
            _get_renderer(),  # !!! render processors must be the last of the chain:
        ],
        # context_class=dict,
        logger_factory=(
            structlog.PrintLoggerFactory()
            if settings.JSON_LOGS is False
            else
            structlog.WriteLoggerFactory(file=_log_dir.open("wt"))),
    )

    root_logger = logging.getLogger()

    def handle_exception(exc_type, exc_value, exc_traceback):
        """
        Логирует любое непойманное исключение вместо его вывода на печать
        Python'ом (кроме KeyboardInterrupt, чтобы позволить Ctrl+C
        для остановки).
        См. https://stackoverflow.com/a/16993115/3641865
        """
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        root_logger.error(
            "Непойманное исключение",
            exc_info=(exc_type, exc_value, exc_traceback),
        )

    sys.excepthook = handle_exception
