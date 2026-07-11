"""Tests for LangSmith configuration."""

import os

from app.core.config import Settings
from observability.langsmith import configure_langsmith, is_langsmith_enabled


def test_configure_langsmith_disabled_sets_tracing_false() -> None:
    """With LangSmith disabled, tracing should be explicitly turned off."""
    settings = Settings(enable_langsmith=False)

    enabled = configure_langsmith(settings)

    assert enabled is False
    assert os.environ["LANGCHAIN_TRACING_V2"] == "false"


def test_configure_langsmith_enabled_without_key_stays_disabled() -> None:
    """Enabling LangSmith without an API key should not turn tracing on."""
    settings = Settings(enable_langsmith=True, langsmith_api_key="")

    enabled = configure_langsmith(settings)

    assert enabled is False


def test_configure_langsmith_enabled_with_key_sets_environment() -> None:
    """A valid configuration should set all required environment variables."""
    settings = Settings(
        enable_langsmith=True,
        langsmith_api_key="test-key",
        langsmith_project="test-project",
    )

    enabled = configure_langsmith(settings)

    assert enabled is True
    assert os.environ["LANGCHAIN_TRACING_V2"] == "true"
    assert os.environ["LANGCHAIN_API_KEY"] == "test-key"
    assert os.environ["LANGCHAIN_PROJECT"] == "test-project"


def test_is_langsmith_enabled_reflects_configuration() -> None:
    """is_langsmith_enabled should require both the flag and an API key."""
    disabled_settings = Settings(enable_langsmith=False, langsmith_api_key="key")
    missing_key_settings = Settings(enable_langsmith=True, langsmith_api_key="")
    valid_settings = Settings(enable_langsmith=True, langsmith_api_key="key")

    assert is_langsmith_enabled(disabled_settings) is False
    assert is_langsmith_enabled(missing_key_settings) is False
    assert is_langsmith_enabled(valid_settings) is True
