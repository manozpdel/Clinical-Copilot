"""Application configuration module.

Defines strongly-typed application settings loaded from environment
variables and `.env` files using pydantic-settings.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings.

    Attributes:
        app_name: Human-readable name of the application.
        app_version: Semantic version of the application.
        environment: Deployment environment identifier (e.g. "development",
            "production").
        debug: Whether debug mode is enabled.
        log_level: Minimum log level emitted by the logging system.
        host: Host interface the application binds to.
        port: Port the application listens on.
    """

    app_name: str = "Clinical Copilot API"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached instance of the application settings.

    Using an LRU cache ensures the settings object is constructed once
    and reused across the application lifecycle.

    Returns:
        Settings: The cached application settings instance.
    """
    return Settings()