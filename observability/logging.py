"""Structured logging context helpers.

This module is responsible ONLY for binding/clearing structured log
context (request_id, correlation_id, user_id, conversation_id,
endpoint, component, latency) via `structlog.contextvars`, so every
log emitted for the duration of a request automatically includes them.
It contains no logger configuration (see `app.core.logging`, which
already configures structlog's processor chain, JSON rendering, and
`merge_contextvars` processor) or tracing/metrics logic.
"""

from typing import Any

import structlog

from app.core.logging import get_logger as get_logger  # noqa: F401 (re-exported)


def bind_request_context(
    request_id: str | None = None,
    correlation_id: str | None = None,
    user_id: str | None = None,
    conversation_id: str | None = None,
    endpoint: str | None = None,
    component: str | None = None,
) -> None:
    """Bind request-scoped fields onto the structlog context.

    Any field left as None is omitted rather than bound as a literal
    "None" string, so partial binding (e.g. only `component`) is safe.

    Args:
        request_id: Unique identifier for this request.
        correlation_id: Identifier correlating this request to a
            broader logical unit of work.
        user_id: Identifier of the authenticated user, if any.
        conversation_id: Identifier of the active conversation, if any.
        endpoint: The API endpoint path being served.
        component: Name of the component emitting subsequent logs
            (e.g. "api", "agent", "voice").
    """
    fields: dict[str, Any] = {
        "request_id": request_id,
        "correlation_id": correlation_id,
        "user_id": user_id,
        "conversation_id": conversation_id,
        "endpoint": endpoint,
        "component": component,
    }
    structlog.contextvars.bind_contextvars(
        **{key: value for key, value in fields.items() if value is not None}
    )


def clear_request_context() -> None:
    """Clear all structlog context bound for the current request/task."""
    structlog.contextvars.clear_contextvars()
