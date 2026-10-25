import logging
import logging.handlers
import os
import sys

import structlog

from src.config.settings import settings


def setup_logging():
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)

    json_renderer = structlog.processors.JSONRenderer()
    console_renderer = structlog.dev.ConsoleRenderer()

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.CallsiteParameterAdder(
            parameters=[
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.LINENO,
                structlog.processors.CallsiteParameter.FUNC_NAME,
                structlog.processors.CallsiteParameter.MODULE,
            ]
        ),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        _add_service_context,
    ]

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=os.path.join("logs", f"{settings.APP_NAME}.log"),
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.suffix = "%Y-%m-%d"

    error_file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=os.path.join("logs", "errors.log"),
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.suffix = "%Y-%m-%d"

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers = [console_handler, file_handler, error_file_handler]

    structlog.configure(
        processors=shared_processors + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=console_renderer if settings.ENV == "local" else json_renderer,
        foreign_pre_chain=shared_processors,
    )

    console_handler.setFormatter(formatter)

    file_handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processor=json_renderer,
            foreign_pre_chain=shared_processors,
        )
    )

    error_file_handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processor=json_renderer,
            foreign_pre_chain=shared_processors,
        )
    )


def _add_service_context(logger, method, event_dict):
    event_dict["service"] = settings.APP_NAME
    event_dict["env"] = settings.ENV
    event_dict["version"] = settings.APP_VERSION
    return event_dict


def get_logger(name: str = __name__):
    return structlog.get_logger(name)
