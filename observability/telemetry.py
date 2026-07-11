"""Single entry point wiring together the observability subsystems.

This module is responsible ONLY for orchestrating initialization of
tracing, instrumentation, and LangSmith at application startup. It
contains no logging, metrics, or health-check logic of its own.
"""

from typing import Any

from app.core.config import Settings
from app.core.logging import get_logger
from observability.langsmith import configure_langsmith
from observability.tracing import init_tracing, instrument_fastapi, instrument_sqlalchemy

logger = get_logger(__name__)


def configure_observability(
    settings: Settings, app: Any = None, engine: Any = None
) -> None:
    """Initialize tracing, FastAPI/SQLAlchemy instrumentation, and LangSmith.

    Args:
        settings: Active application settings.
        app: Optional FastAPI application instance to instrument.
        engine: Optional async SQLAlchemy engine to instrument.
    """
    init_tracing(settings)

    if settings.enable_tracing:
        if app is not None:
            instrument_fastapi(app)
        if engine is not None:
            instrument_sqlalchemy(engine)

    langsmith_enabled = configure_langsmith(settings)

    logger.info(
        "observability_configured",
        tracing_enabled=settings.enable_tracing,
        metrics_enabled=settings.enable_metrics,
        langsmith_enabled=langsmith_enabled,
    )
