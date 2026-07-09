"""Tests for the static frontend mount."""

from fastapi.testclient import TestClient

from app.main import app


def test_frontend_index_loads_successfully() -> None:
    """GET /app/ should serve the frontend's index.html."""
    client = TestClient(app)

    response = client.get("/app/")

    assert response.status_code == 200
    assert "Clinical Copilot" in response.text
    assert "text/html" in response.headers["content-type"]


def test_frontend_serves_static_assets() -> None:
    """Static assets like app.js and styles.css should be reachable."""
    client = TestClient(app)

    js_response = client.get("/app/app.js")
    css_response = client.get("/app/styles.css")

    assert js_response.status_code == 200
    assert css_response.status_code == 200