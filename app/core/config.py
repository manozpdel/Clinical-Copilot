"""Application configuration module.

Defines strongly-typed application settings loaded from environment
variables and `.env` files using pydantic-settings.
"""

from functools import lru_cache
from pathlib import Path

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
        patient_count: Number of synthetic patient records to generate.
        chunk_size: Number of words per document chunk.
        chunk_overlap: Number of overlapping words between consecutive
            chunks.
        collection_name: Name of the Chroma collection used to store
            clinical note embeddings.
        embedding_model: Name of the FastEmbed embedding model to use.
        chroma_path: Filesystem path where the Chroma database is
            persisted.
        data_raw_dir: Directory where raw synthetic patient text files are
            written.
        data_processed_dir: Directory reserved for processed data
            artifacts.
    """

    app_name: str = "Clinical Copilot API"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8000

    patient_count: int = 20
    chunk_size: int = 500
    chunk_overlap: int = 50
    collection_name: str = "clinical_notes"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    chroma_path: Path = Path("chroma_db")
    data_raw_dir: Path = Path("data/raw/patients")
    data_processed_dir: Path = Path("data/processed")

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