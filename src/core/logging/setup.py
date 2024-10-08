"""
Основная настройка structlog
src/core/logging/setup.py
"""
import logging
import logging.config
import os
import sys

import structlog
import ujson
from src.settings import settings
from structlog.types import EventDict, Processor


os.makedirs(settings.LOG_DIR, exist_ok=True)


def _drop_color_message_key(_, __, event_dict: EventDict) -> EventDict:
    """
    Uvicorn логирует сообщение повторно в дополнительной секции
    `color_message`. Данная функция ("процессор") убирает данный ключ из event dict.
    В логах в файле отсутствуе ответ апи из-за ее наличия!
    """
    event_dict.pop("color_message", None)
    return event_dict


def _get_renderer() -> structlog.processors.JSONRenderer | structlog.dev.ConsoleRenderer:
    """Получаем рендерер на основании параметров среды: возвращаем рендерер structlog."""
    if settings.JSON_LOGS is False:
        return structlog.dev.ConsoleRenderer(colors=True)
    return structlog.processors.JSONRenderer(
        indent=2,
        sort_keys=True,
        serializer=ujson.dumps,
        ensure_ascii=False,
    )

TIMESTAMPER = structlog.processors.TimeStamper(fmt="iso", utc=False)

PRE_CHAIN: list[Processor] = [
    structlog.contextvars.merge_contextvars,  # объединяет контекстные переменные: инфу о запросе, времени, юзере и тп.
    structlog.stdlib.add_logger_name,
    structlog.stdlib.add_log_level,
    structlog.stdlib.PositionalArgumentsFormatter(),
    structlog.stdlib.ExtraAdder(),
    #  Uvicorn логирует сообщение повторно ("процессор") убирает данный ключ из event dict.
    # _drop_color_message_key,  # и убивает в файле логов ответ апи (отключили для записи логов в файл) !!!
    TIMESTAMPER,
    structlog.processors.dict_tracebacks,  # ! процессор, для обработки исключений (трассировки стека)
    structlog.processors.StackInfoRenderer(),  # ! процессор, обрабатывающий выходные данные, дб последним в цепочке
]


LOGGING_DICTCONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "plain": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processors": [
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                _get_renderer(),
            ],
            "foreign_pre_chain": PRE_CHAIN,
        },
        "colored": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processors": [
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.dev.ConsoleRenderer(colors=True),
                # _get_renderer(),
            ],
            "foreign_pre_chain": PRE_CHAIN,
        },
    },
    "handlers": {
        "default": {
            "level": settings.LOG_LEVEL,
            "class": "logging.StreamHandler",
            "formatter": "plain" if settings.JSON_LOGS is True else "colored",
        },
        "file": {
            "level": settings.LOG_LEVEL,
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(settings.LOG_DIR, settings.LOG_FILE),
            "mode": "a",
            "maxBytes": settings.LOG_FILE_SIZE,
            "backupCount": settings.LOG_FILES_TO_KEEP,
            "encoding": "UTF-8",
            # set json or string logs in file
            "formatter": "plain" if settings.JSON_LOGS is True else "colored",
        },
    },
    "loggers": {
        "": {
            "handlers": ["default", "file"],
            "level": settings.LOG_LEVEL,
            "propagate": True,
        },
    },
}


def _setup_structlog():
    """Настройки structlog."""

    logging.config.dictConfig(LOGGING_DICTCONFIG)

    structlog.configure(
        processors=PRE_CHAIN
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def _setup_structlog_pretty():
    """Альтернативная настройка structlog_pretty."""

    logging.config.dictConfig(LOGGING_DICTCONFIG)

    structlog.configure(
        processors=PRE_CHAIN
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def _setup_uvicorn_logging():
    """Настройки логирования uvicorn."""
    for _log in logging.root.manager.loggerDict.keys():
        logging.getLogger(_log).handlers.clear()
        logging.getLogger(_log).propagate = True

    logging.getLogger("uvicorn.access").handlers.clear()
    logging.getLogger("uvicorn.access").propagate = False


def setup_logging():
    """Основные настройки логирования."""
    _setup_structlog()
    # _setup_structlog_pretty
    _setup_uvicorn_logging()

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
