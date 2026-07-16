"""Application entry point for the Clinical Copilot FastAPI service."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api import health
from app.api.auth import router as auth_router
from app.api.router import api_router
from app.core.config import get_settings
from app.core.constants import ROOT_MESSAGE
from app.core.logging import configure_logging, get_logger
from auth.dependencies import get_current_user
from database.models import User
from database.session import engine
from feedback.router import router as feedback_router
from observability.health import HealthService
from observability.middleware import ObservabilityMiddleware
from observability.models import HealthSummary
from observability.telemetry import configure_observability
from security.headers import SecurityHeadersMiddleware
from security.limiter import limiter, rate_limit_exceeded_handler
from security.middleware import (
    AuthContextMiddleware,
    RequestIDMiddleware,
    RequestSizeLimitMiddleware,
    RequestTimingMiddleware,
)
from streaming.sse import router as streaming_sse_router
from streaming.websocket import router as streaming_ws_router

configure_logging()
logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown logging."""
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

configure_observability(settings, app=app, engine=engine)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(ObservabilityMiddleware, settings=settings)

if settings.enable_security_headers:
    app.add_middleware(SecurityHeadersMiddleware, settings=settings)

app.add_middleware(RequestTimingMiddleware)
app.add_middleware(RequestSizeLimitMiddleware, settings=settings)
app.add_middleware(AuthContextMiddleware, settings=settings)
app.add_middleware(RequestIDMiddleware)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(settings.trusted_hosts))
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.trusted_hosts),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth_router)
app.include_router(api_router)
app.include_router(feedback_router)
app.include_router(streaming_sse_router)
app.include_router(streaming_ws_router)

if settings.enable_frontend and settings.static_files_path.exists():
    app.mount(
        "/app",
        StaticFiles(directory=str(settings.static_files_path), html=True),
        name="frontend",
    )


@app.get("/")
async def read_root() -> dict[str, str]:
    """Return the root welcome message for the API."""
    return {"message": ROOT_MESSAGE}


@app.get("/metrics")
async def get_metrics() -> Response:
    """Expose Prometheus metrics in text exposition format."""
    if not settings.prometheus_enabled:
        raise HTTPException(status_code=404, detail="Metrics endpoint disabled.")
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/health/detailed", response_model=HealthSummary)
async def get_detailed_health(
    current_user: User = Depends(get_current_user),
) -> HealthSummary:
    """Return a detailed health summary of every application dependency."""
    service = HealthService(settings)
    return await service.get_summary()
