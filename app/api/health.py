"""Health check API routes."""

from fastapi import APIRouter

from app.core.constants import HEALTH_STATUS_HEALTHY
from app.core.logging import get_logger

router = APIRouter(tags=["health"])
logger = get_logger(__name__)


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Return the current health status of the application.

    Returns:
        dict[str, str]: A mapping containing the application's health
            status.
    """
    logger.info("health_check_requested")
    return {"status": HEALTH_STATUS_HEALTHY}
