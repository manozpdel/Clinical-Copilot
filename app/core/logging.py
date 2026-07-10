"""Structured logging configuration using structlog.

This module configures application-wide structured logging and exposes
a factory function for obtaining bound loggers.
"""

import logging
import sys

import structlog

from app.core.config import get_settings


def configure_logging() -> None:
    """Configure structlog and the standard library logging integration.

    This sets up JSON-renderable structured logging with consistent
    timestamps, log levels, and processor chains suitable for production
    observability pipelines.
    """
    settings = get_settings()

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=settings.log_level.upper(),
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.log_level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger for the given name.

    Args:
        name: Logical name of the logger, typically `__name__` of the
            calling module.

    Returns:
        structlog.stdlib.BoundLogger: A structured logger instance bound
            to the provided name.
    """
    return structlog.get_logger(name)
