"""Top-level API router aggregation.

This module is responsible ONLY for registering sub-routers and the
two trivial system endpoints (health, version) under the shared
`/api` prefix. It contains no business logic.
"""

from fastapi import APIRouter

from app.api import citations, evaluation, query, voice
from app.core.config import get_settings
from app.schemas.responses import HealthResponse, VersionResponse

api_router = APIRouter(prefix="/api")


@api_router.get("/health", response_model=HealthResponse, tags=["system"])
async def get_api_health() -> HealthResponse:
    """Return the current health status of the REST API.

    Returns:
        HealthResponse: A mapping containing the API's health status.
    """
    return HealthResponse(status="healthy")


@api_router.get("/version", response_model=VersionResponse, tags=["system"])
async def get_api_version() -> VersionResponse:
    """Return the current API version, environment, and status.

    Returns:
        VersionResponse: The API version, active environment, and
            operational status.
    """
    settings = get_settings()
    return VersionResponse(
        version=settings.api_version,
        environment=settings.environment,
        status="operational",
    )


api_router.include_router(query.router)
api_router.include_router(voice.router)
api_router.include_router(citations.router)
api_router.include_router(evaluation.router)