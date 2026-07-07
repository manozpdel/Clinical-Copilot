"""Tests for the root and health check endpoints."""

from httpx import ASGITransport, AsyncClient

from app.core.constants import HEALTH_STATUS_HEALTHY, ROOT_MESSAGE
from app.main import app


async def test_read_root() -> None:
    """The root endpoint should return the expected welcome message."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": ROOT_MESSAGE}


async def test_health_check() -> None:
    """The health endpoint should return a healthy status."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": HEALTH_STATUS_HEALTHY}