"""Request rate limiting.

This module is responsible ONLY for configuring the slowapi rate
limiter and its key function. It contains no quota, cost, or
persistence logic. The key function prefers the authenticated user's
ID (populated onto `request.state.user_id` by
`security.middleware.AuthContextMiddleware`) and falls back to the
client's IP address for unauthenticated requests.
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import get_settings


def user_or_ip_key(request: Request) -> str:
    """Derive the rate-limit key for a request.

    Args:
        request: The incoming HTTP request.

    Returns:
        str: `"user:<id>"` if an authenticated user was resolved for
            this request by `AuthContextMiddleware`, otherwise
            `"ip:<address>"`.
    """
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"
    return f"ip:{get_remote_address(request)}"


limiter = Limiter(key_func=user_or_ip_key, enabled=get_settings().enable_rate_limiting)


def rate_limit_string() -> str:
    """Build the dynamic slowapi limit string from application settings.

    slowapi invokes dynamic limit callables with no arguments, so this
    function reads settings directly rather than accepting a request.

    Returns:
        str: A slowapi limit expression combining the configured
            per-minute and per-hour limits.
    """
    settings = get_settings()
    return f"{settings.rate_limit_per_minute}/minute;{settings.rate_limit_per_hour}/hour"


async def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    """Return a structured HTTP 429 response for rate-limited requests.

    Args:
        request: The incoming HTTP request.
        exc: The raised rate-limit-exceeded exception.

    Returns:
        JSONResponse: A 429 response with a descriptive error detail.
    """
    return JSONResponse(
        status_code=429,
        content={"detail": f"Rate limit exceeded: {exc.detail}"},
    )
