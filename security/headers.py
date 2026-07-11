"""Security response headers.

This module is responsible ONLY for attaching standard security
headers to every response. It contains no request-context, timing, or
size-limiting logic (see `security.middleware`).
"""

import logging

from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.config import Settings

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware:
    """Attaches standard security headers to every response using pure ASGI."""

    def __init__(self, app: ASGIApp, settings: Settings) -> None:
        """Initialize the middleware with the active application settings.

        Args:
            app: The ASGI application to wrap.
            settings: Active application settings, providing the CSP
                policy string.
        """
        self.app = app
        self._csp_policy = settings.csp_policy
        # Debug log
        logger.info(f"SecurityHeadersMiddleware initialized with CSP: {self._csp_policy}")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Attach security headers to the downstream response.

        Intercepts the HTTP response start message and injects security
        headers before passing the message downstream. Non-HTTP scopes
        (e.g., WebSocket) are passed through unchanged.

        Args:
            scope: The ASGI connection scope.
            receive: The ASGI receive channel.
            send: The ASGI send channel.
        """
        # Only process HTTP requests
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message: dict) -> None:
            """Intercept response start and inject security headers.

            Args:
                message: The ASGI message being sent. Modified in-place
                    when it is an ``http.response.start`` message.
            """
            if message["type"] == "http.response.start":
                # Convert existing headers to a mutable dict
                headers = dict(message.get("headers", []))

                # Debug log
                logger.debug(f"Adding CSP header: {self._csp_policy}")

                # Add or overwrite security headers
                headers[b"x-content-type-options"] = b"nosniff"
                headers[b"x-frame-options"] = b"DENY"
                headers[b"referrer-policy"] = b"strict-origin-when-cross-origin"
                headers[b"content-security-policy"] = self._csp_policy.encode()
                headers[b"strict-transport-security"] = (
                    b"max-age=63072000; includeSubDomains"
                )

                # Convert back to list of tuples for ASGI spec
                message["headers"] = list(headers.items())

            await send(message)

        await self.app(scope, receive, send_wrapper)
