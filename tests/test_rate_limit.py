"""Tests for the rate-limit key function and dynamic limit string."""

from unittest.mock import MagicMock

from app.core.config import get_settings
from security.limiter import rate_limit_string, user_or_ip_key


def test_user_or_ip_key_prefers_authenticated_user() -> None:
    """When request.state.user_id is set, the key should be user-based."""
    request = MagicMock()
    request.state.user_id = "abc-123"

    assert user_or_ip_key(request) == "user:abc-123"


def test_user_or_ip_key_falls_back_to_ip() -> None:
    """When no user_id is present, the key should be IP-based."""
    request = MagicMock()
    request.state.user_id = None
    request.client.host = "127.0.0.1"
    request.headers = {}

    key = user_or_ip_key(request)

    assert key.startswith("ip:")


def test_rate_limit_string_reflects_settings() -> None:
    """The dynamic limit string should include the configured per-minute limit."""
    settings = get_settings()

    limit_string = rate_limit_string()

    assert str(settings.rate_limit_per_minute) in limit_string
    assert "minute" in limit_string
    assert "hour" in limit_string
