"""Application entry point for the Clinical Copilot FastAPI service."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api import health
from app.api.auth import router as auth_router
from app.api.router import api_router
from app.core.config import get_settings
from app.core.constants import ROOT_MESSAGE
from app.core.logging import configure_logging, get_logger
from security.headers import SecurityHeadersMiddleware
from security.limiter import limiter, rate_limit_exceeded_handler
from security.middleware import (
    AuthContextMiddleware,
    RequestIDMiddleware,
    RequestSizeLimitMiddleware,
    RequestTimingMiddleware,
)

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

# ---------------------------------------------------------------------------
# Middleware stack
# ---------------------------------------------------------------------------
# NOTE: Middleware is applied in REVERSE order – the last middleware added
# wraps the outermost layer and therefore runs first on the way in and last
# on the way out. SecurityHeadersMiddleware is added last so it can
# intercept EVERY response, including those served by StaticFiles.
# ---------------------------------------------------------------------------

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

app.add_middleware(SlowAPIMiddleware)
app.add_middleware(RequestTimingMiddleware)
app.add_middleware(RequestSizeLimitMiddleware, settings=settings)
app.add_middleware(AuthContextMiddleware, settings=settings)
app.add_middleware(RequestIDMiddleware)

app.add_middleware(
    TrustedHostMiddleware, allowed_hosts=list(settings.trusted_hosts)
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.trusted_hosts),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security headers middleware MUST be added LAST so it wraps all other
# middleware and static file handlers, guaranteeing headers are attached
# to every response.
if settings.enable_security_headers:
    app.add_middleware(SecurityHeadersMiddleware, settings=settings)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(health.router)
app.include_router(auth_router)
app.include_router(api_router)

# ---------------------------------------------------------------------------
# Static files (frontend)
# ---------------------------------------------------------------------------
if settings.enable_frontend and settings.static_files_path.exists():
    app.mount(
        "/app",
        StaticFiles(directory=str(settings.static_files_path), html=True),
        name="frontend",
    )


@app.get("/")
async def read_root() -> dict[str, str]:
    """Return the root welcome message for the API.

    Returns:
        dict[str, str]: A mapping containing the API's welcome message.
    """
    return {"message": ROOT_MESSAGE}
