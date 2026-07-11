"""Tests for security response headers."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from security.headers import SecurityHeadersMiddleware


def _build_test_app(settings: Settings) -> FastAPI:
    """Build a minimal FastAPI app wired with SecurityHeadersMiddleware.

    Args:
        settings: Application settings providing the CSP policy.

    Returns:
        FastAPI: The configured test application.
    """
    app = FastAPI()

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        return {"status": "ok"}

    app.add_middleware(SecurityHeadersMiddleware, settings=settings)
    return app


def test_security_headers_are_present() -> None:
    """All expected security headers should be present on every response."""
    settings = Settings(csp_policy="default-src 'self'")
    client = TestClient(_build_test_app(settings))

    response = client.get("/ping")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response.headers["Content-Security-Policy"] == "default-src 'self'"
    assert "Strict-Transport-Security" in response.headers
