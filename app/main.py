"""Application entry point for the Clinical Copilot FastAPI service."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import health
from app.core.config import get_settings
from app.core.constants import ROOT_MESSAGE
from app.core.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown logging.

    Args:
        app: The FastAPI application instance.

    Yields:
        None: Control is yielded back to FastAPI while the application runs.
    """
    logger.info(
        "application_startup",
        app_name=settings.app_name,
        environment=settings.environment,
    )
    yield
    logger.info("application_shutdown")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
)

app.include_router(health.router)


@app.get("/")
async def read_root() -> dict[str, str]:
    """Return the root welcome message for the API.

    Returns:
        dict[str, str]: A mapping containing the API's welcome message.
    """
    return {"message": ROOT_MESSAGE}