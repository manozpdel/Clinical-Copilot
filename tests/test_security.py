"""Tests for request-context security middleware."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from security.middleware import (
    AuthContextMiddleware,
    RequestIDMiddleware,
    RequestSizeLimitMiddleware,
    RequestTimingMiddleware,
)


def _build_test_app(settings: Settings) -> FastAPI:
    """Build a minimal FastAPI app wired with the security middleware stack.

    Args:
        settings: Application settings to configure the middleware.

    Returns:
        FastAPI: The configured test application.
    """
    app = FastAPI()

    @app.post("/echo")
    async def echo() -> dict[str, str]:
        return {"ok": "true"}

    app.add_middleware(RequestTimingMiddleware)
    app.add_middleware(RequestSizeLimitMiddleware, settings=settings)
    app.add_middleware(AuthContextMiddleware, settings=settings)
    app.add_middleware(RequestIDMiddleware)

    return app


def test_request_id_header_is_added() -> None:
    """Every response should include a unique X-Request-ID header."""
    settings = Settings(max_request_size_mb=10.0)
    client = TestClient(_build_test_app(settings))

    response = client.post("/echo", json={})

    assert "X-Request-ID" in response.headers


def test_request_timing_header_is_added() -> None:
    """Every response should include an X-Process-Time-Ms header."""
    settings = Settings(max_request_size_mb=10.0)
    client = TestClient(_build_test_app(settings))

    response = client.post("/echo", json={})

    assert "X-Process-Time-Ms" in response.headers


def test_oversized_request_is_rejected() -> None:
    """A request declaring a body larger than the configured limit should get a 413."""
    settings = Settings(max_request_size_mb=0.000001)
    client = TestClient(_build_test_app(settings))

    response = client.post("/echo", json={"padding": "x" * 5000})

    assert response.status_code == 413
