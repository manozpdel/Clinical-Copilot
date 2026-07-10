"""Tests for Google OAuth ID token verification."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.core.config import Settings
from auth.oauth import GoogleOAuthError, verify_google_id_token


def _settings() -> Settings:
    """Build settings with a fixed Google client ID for deterministic tests.

    Returns:
        Settings: Application settings with a test Google client ID.
    """
    return Settings(google_client_id="test-client-id")


def _fake_response(status_code: int, payload: dict) -> httpx.Response:
    """Build a fake httpx.Response for mocking Google's tokeninfo endpoint.

    Args:
        status_code: The HTTP status code to simulate.
        payload: The JSON payload to return.

    Returns:
        httpx.Response: The constructed fake response.
    """
    return httpx.Response(
        status_code=status_code,
        json=payload,
        request=httpx.Request("GET", "https://oauth2.googleapis.com/tokeninfo"),
    )


async def test_verify_google_id_token_returns_profile_on_success() -> None:
    """A valid token response should yield a GoogleProfile."""
    settings = _settings()
    fake_response = _fake_response(
        200, {"aud": "test-client-id", "email": "user@example.com", "name": "Test User"}
    )

    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=fake_response)):
        profile = await verify_google_id_token("fake-token", settings)

    assert profile.email == "user@example.com"
    assert profile.name == "Test User"


async def test_verify_google_id_token_rejects_non_200_response() -> None:
    """A non-200 response from Google should raise GoogleOAuthError."""
    settings = _settings()
    fake_response = _fake_response(400, {"error": "invalid_token"})

    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=fake_response)):
        with pytest.raises(GoogleOAuthError):
            await verify_google_id_token("bad-token", settings)


async def test_verify_google_id_token_rejects_audience_mismatch() -> None:
    """A token issued for a different client ID should raise GoogleOAuthError."""
    settings = _settings()
    fake_response = _fake_response(
        200, {"aud": "some-other-client-id", "email": "user@example.com"}
    )

    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=fake_response)):
        with pytest.raises(GoogleOAuthError):
            await verify_google_id_token("fake-token", settings)


async def test_verify_google_id_token_rejects_missing_email() -> None:
    """A token response without an email claim should raise GoogleOAuthError."""
    settings = _settings()
    fake_response = _fake_response(200, {"aud": "test-client-id"})

    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=fake_response)):
        with pytest.raises(GoogleOAuthError):
            await verify_google_id_token("fake-token", settings)
