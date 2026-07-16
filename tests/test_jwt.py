"""Tests for JWT access/refresh token creation and verification."""

import uuid

import pytest

from app.core.config import Settings
from auth.jwt import TokenError, create_access_token, create_refresh_token, decode_token


def _settings() -> Settings:
    """Build settings with a fixed JWT secret for deterministic tests.

    Returns:
        Settings: Application settings with a test JWT secret key.
    """
    return Settings(jwt_secret_key="test-secret-key")


def test_access_token_round_trip() -> None:
    """A created access token should decode back to its original subject."""
    settings = _settings()
    user_id = uuid.uuid4()

    token = create_access_token(user_id, settings)
    subject = decode_token(token, settings, expected_type="access")

    assert subject == str(user_id)


def test_refresh_token_round_trip() -> None:
    """A created refresh token should decode back to its original subject."""
    settings = _settings()
    user_id = uuid.uuid4()

    token = create_refresh_token(user_id, settings)
    subject = decode_token(token, settings, expected_type="refresh")

    assert subject == str(user_id)


def test_decode_rejects_wrong_token_type() -> None:
    """An access token should be rejected when a refresh token is expected."""
    settings = _settings()
    token = create_access_token(uuid.uuid4(), settings)

    with pytest.raises(TokenError):
        decode_token(token, settings, expected_type="refresh")


def test_decode_rejects_expired_token() -> None:
    """A token with a negative lifetime should be rejected as expired."""
    settings = Settings(jwt_secret_key="test-secret-key", access_token_expire_minutes=-1)
    token = create_access_token(uuid.uuid4(), settings)

    with pytest.raises(TokenError):
        decode_token(token, settings, expected_type="access")


def test_decode_rejects_garbage_token() -> None:
    """A malformed token string should be rejected."""
    settings = _settings()

    with pytest.raises(TokenError):
        decode_token("not-a-real-token", settings, expected_type="access")
