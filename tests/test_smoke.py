"""Lightweight smoke tests: the app must import and construct cleanly."""

from fastapi.testclient import TestClient

from app.main import app


def test_app_imports_and_constructs() -> None:
    """The FastAPI app object should exist and expose routes."""
    assert app is not None
    assert len(app.routes) > 0


def test_root_and_health_respond() -> None:
    """Root and health endpoints should respond successfully with no auth."""
    client = TestClient(app)

    assert client.get("/").status_code == 200
    assert client.get("/health").status_code == 200


def test_openapi_schema_generates() -> None:
    """The OpenAPI schema should generate without error (validates all routes)."""
    client = TestClient(app)

    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "paths" in response.json()