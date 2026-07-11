"""Security-related ASGI middleware.

This module is responsible ONLY for request-level middleware:
request ID generation, request timing, request size limiting, and
best-effort authentication context extraction (used only to key rate
limiting, not to authorize requests — actual authorization remains the
responsibility of `auth.dependencies.get_current_user`). It contains no
security headers (see `security.headers`) or validation-utility logic
(see `security.validators`).
"""

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import Settings
from app.core.logging import get_logger
from auth.jwt import TokenError, decode_token

logger = get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Assigns a unique request ID to every request and response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        """Attach a generated request ID to the request and response.

        Args:
            request: The incoming HTTP request.
            call_next: The next handler in the middleware chain.

        Returns:
            Response: The downstream response, with an `X-Request-ID`
                header added.
        """
        request_id = uuid.uuid4().hex
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Logs request processing time and returns it as a response header."""

    async def dispatch(self, request: Request, call_next) -> Response:
        """Time request processing and record it in logs and headers.

        Args:
            request: The incoming HTTP request.
            call_next: The next handler in the middleware chain.

        Returns:
            Response: The downstream response, with an
                `X-Process-Time-Ms` header added.
        """
        start_time = time.monotonic()
        response = await call_next(request)
        elapsed_ms = (time.monotonic() - start_time) * 1000

        logger.info(
            "request_completed",
            path=request.url.path,
            method=request.method,
            status_code=response.status_code,
            elapsed_ms=round(elapsed_ms, 2),
        )
        response.headers["X-Process-Time-Ms"] = str(round(elapsed_ms, 2))
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Rejects requests whose declared body size exceeds the configured limit."""

    def __init__(self, app, settings: Settings) -> None:
        """Initialize the middleware with the configured size limit.

        Args:
            app: The ASGI application to wrap.
            settings: Active application settings, providing
                `max_request_size_mb`.
        """
        super().__init__(app)
        self._max_bytes = int(settings.max_request_size_mb * 1024 * 1024)

    async def dispatch(self, request: Request, call_next) -> Response:
        """Reject oversized requests before they reach route handlers.

        Args:
            request: The incoming HTTP request.
            call_next: The next handler in the middleware chain.

        Returns:
            Response: A 413 JSON response if the declared
                `Content-Length` exceeds the configured limit,
                otherwise the downstream response.
        """
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > self._max_bytes:
                    return JSONResponse(
                        status_code=413,
                        content={"detail": "Request body exceeds the maximum allowed size."},
                    )
            except ValueError:
                pass

        return await call_next(request)


class AuthContextMiddleware(BaseHTTPMiddleware):
    """Best-effort extraction of the requester's user ID from a bearer JWT.

    This middleware never authenticates or authorizes a request — it
    only populates `request.state.user_id` (when a valid access token
    is present) so that `security.limiter.user_or_ip_key` can key rate
    limits by user rather than by IP for authenticated traffic. Actual
    authorization is still enforced exclusively by
    `auth.dependencies.get_current_user`.
    """

    def __init__(self, app, settings: Settings) -> None:
        """Initialize the middleware with the active application settings.

        Args:
            app: The ASGI application to wrap.
            settings: Active application settings, providing the JWT
                signing key and algorithm.
        """
        super().__init__(app)
        self._settings = settings

    async def dispatch(self, request: Request, call_next) -> Response:
        """Populate `request.state.user_id` from a valid bearer token, if any.

        Args:
            request: The incoming HTTP request.
            call_next: The next handler in the middleware chain.

        Returns:
            Response: The downstream response, unmodified.
        """
        request.state.user_id = None

        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:]
            try:
                request.state.user_id = decode_token(
                    token, self._settings, expected_type="access"
                )
            except TokenError:
                pass

        return await call_next(request)
