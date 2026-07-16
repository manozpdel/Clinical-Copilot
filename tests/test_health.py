"""Tests for application dependency health checks."""

from app.core.config import Settings
from observability.health import HealthService


def test_check_groq_healthy_when_key_configured() -> None:
    """A configured Groq API key should report a healthy status."""
    settings = Settings(generation_api_key="test-key")
    service = HealthService(settings)

    result = service.check_groq()

    assert result.status == "healthy"


def test_check_groq_unhealthy_when_key_missing() -> None:
    """A missing Groq API key should report an unhealthy status."""
    settings = Settings(generation_api_key="")
    service = HealthService(settings)

    result = service.check_groq()

    assert result.status == "unhealthy"


def test_check_langsmith_disabled_by_default() -> None:
    """LangSmith should report 'disabled' when the feature flag is off."""
    settings = Settings(enable_langsmith=False)
    service = HealthService(settings)

    result = service.check_langsmith()

    assert result.status == "disabled"


def test_check_langsmith_unhealthy_without_key() -> None:
    """Enabling LangSmith without a key should report unhealthy."""
    settings = Settings(enable_langsmith=True, langsmith_api_key="")
    service = HealthService(settings)

    result = service.check_langsmith()

    assert result.status == "unhealthy"


def test_check_disk_returns_healthy_or_degraded() -> None:
    """The disk check should always return one of the two expected statuses."""
    settings = Settings()
    service = HealthService(settings)

    result = service.check_disk()

    assert result.status in ("healthy", "degraded")
    assert result.detail is not None


def test_check_memory_returns_healthy_with_detail() -> None:
    """The memory check should always report healthy with a detail string."""
    settings = Settings()
    service = HealthService(settings)

    result = service.check_memory()

    assert result.status == "healthy"
    assert result.detail is not None


async def test_check_database_reports_unhealthy_for_bad_url() -> None:
    """An unreachable database URL should be reported as unhealthy."""
    settings = Settings(database_url="postgresql+asyncpg://baduser:badpass@localhost:1/nonexistent")
    service = HealthService(settings)

    result = await service.check_database()

    assert result.status == "unhealthy"
    assert result.detail is not None
