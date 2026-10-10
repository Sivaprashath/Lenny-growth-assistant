"""
Structured logging setup using structlog for JSON-formatted, observable logs.
Every log entry includes correlation IDs, model provider, and retrieval context.
"""
import logging
import sys
import structlog
from app.core.config import settings


def configure_logging() -> None:
    """Configure structlog for structured JSON output."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.DEBUG:
        renderer = structlog.dev.ConsoleRenderer(colors=True)
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=renderer,
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(log_level)


def get_logger(name: str = __name__) -> structlog.BoundLogger:
    return structlog.get_logger(name)
