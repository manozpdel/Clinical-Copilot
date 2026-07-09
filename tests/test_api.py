"""Tests for the system-level API endpoints (health, version)."""

from fastapi.testclient import TestClient

from app.main import app


def test_api_health_endpoint_returns_healthy() -> None:
    """GET /api/health should report a healthy status."""
    client = TestClient(app)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_api_version_endpoint_returns_expected_fields() -> None:
    """GET /api/version should report version, environment, and status."""
    client = TestClient(app)

    response = client.get("/api/version")

    assert response.status_code == 200
    body = response.json()
    assert "version" in body
    assert "environment" in body
    assert body["status"] == "operational"


def test_root_endpoint_still_works() -> None:
    """The Part 1 root endpoint should remain unaffected by Part 8 additions."""
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "Clinical Copilot API"}


def test_legacy_health_endpoint_still_works() -> None:
    """The Part 1 unprefixed /health endpoint should remain unaffected."""
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}