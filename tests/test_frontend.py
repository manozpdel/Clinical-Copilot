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


def test_frontend_serves_login_page() -> None:
    """GET /app/login.html should serve the login page."""
    client = TestClient(app)

    response = client.get("/app/login.html")

    assert response.status_code == 200
    assert "Sign in with Google" in response.text or "google-button-container" in response.text


def test_frontend_serves_profile_page() -> None:
    """GET /app/profile.html should serve the profile page."""
    client = TestClient(app)

    response = client.get("/app/profile.html")

    assert response.status_code == 200
    assert "profile-card" in response.text


def test_frontend_serves_auth_js_modules() -> None:
    """Each new auth-related JS module should be reachable as a static asset."""
    client = TestClient(app)

    for path in (
        "js/storage.js",
        "js/api.js",
        "js/auth.js",
        "js/router.js",
        "js/guards.js",
        "js/profile.js",
    ):
        response = client.get(f"/app/{path}")
        assert response.status_code == 200, f"{path} was not served"
