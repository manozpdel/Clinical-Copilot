"""Observability middleware.

This module is responsible ONLY for per-request observability
bookkeeping: generating/propagating request and correlation IDs,
binding structured logging context, and recording Prometheus request
metrics. It contains no security enforcement (see `security.middleware`)
and creates no manual tracing spans, since FastAPI's HTTP layer is
already auto-instrumented by `observability.tracing.instrument_fastapi`.
"""

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import Settings
from app.core.logging import get_logger
from observability.logging import bind_request_context, clear_request_context
from observability.metrics import record_error, record_request
from observability.request_id import generate_correlation_id, generate_request_id

logger = get_logger(__name__)


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Binds request/correlation IDs and records per-request metrics."""

    def __init__(self, app, settings: Settings) -> None:
        """Initialize the middleware with the active application settings.

        Args:
            app: The ASGI application to wrap.
            settings: Active application settings, providing
                `enable_metrics`.
        """
        super().__init__(app)
        self._enable_metrics = settings.enable_metrics

    async def dispatch(self, request: Request, call_next) -> Response:
        """Bind observability context and record metrics for a request.

        Args:
            request: The incoming HTTP request.
            call_next: The next handler in the middleware chain.

        Returns:
            Response: The downstream response, with `X-Correlation-ID`
                added.
        """
        request_id = generate_request_id()
        correlation_id = request.headers.get("x-correlation-id") or generate_correlation_id()

        request.state.observability_request_id = request_id
        request.state.correlation_id = correlation_id

        bind_request_context(
            request_id=request_id,
            correlation_id=correlation_id,
            endpoint=request.url.path,
            component="http",
        )

        start = time.monotonic()
        try:
            response = await call_next(request)
        except Exception:
            if self._enable_metrics:
                record_error(request.method, request.url.path)
            clear_request_context()
            raise

        elapsed = time.monotonic() - start
        if self._enable_metrics:
            record_request(request.method, request.url.path, response.status_code, elapsed)

        response.headers["X-Correlation-ID"] = correlation_id
        clear_request_context()
        return response
