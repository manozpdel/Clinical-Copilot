"""Tests for structured logging context binding."""

import structlog
from structlog.testing import LogCapture

from observability.logging import bind_request_context, clear_request_context


def test_bind_request_context_adds_fields_to_logs() -> None:
    """Bound context fields should appear in subsequently emitted logs."""
    capture = LogCapture()
    structlog.configure(processors=[structlog.contextvars.merge_contextvars, capture])

    try:
        bind_request_context(
            request_id="req-1",
            correlation_id="corr-1",
            user_id="user-1",
            conversation_id="conv-1",
            endpoint="/api/query",
            component="api",
        )
        logger = structlog.get_logger()
        logger.info("test_event")
    finally:
        clear_request_context()
        structlog.reset_defaults()

    assert len(capture.entries) == 1
    entry = capture.entries[0]
    assert entry["request_id"] == "req-1"
    assert entry["correlation_id"] == "corr-1"
    assert entry["user_id"] == "user-1"
    assert entry["conversation_id"] == "conv-1"
    assert entry["endpoint"] == "/api/query"
    assert entry["component"] == "api"


def test_clear_request_context_removes_bound_fields() -> None:
    """Clearing context should remove previously bound fields from logs."""
    capture = LogCapture()
    structlog.configure(processors=[structlog.contextvars.merge_contextvars, capture])

    try:
        bind_request_context(request_id="req-2")
        clear_request_context()
        logger = structlog.get_logger()
        logger.info("test_event")
    finally:
        structlog.reset_defaults()

    assert "request_id" not in capture.entries[0]
