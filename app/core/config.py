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
        environment: Deployment environment identifier.
        debug: Whether debug mode is enabled.
        log_level: Minimum log level emitted by the logging system.
        host: Host interface the application binds to.
        port: Port the application listens on.
        patient_count: Number of synthetic patient records to generate.
        chunk_size: Maximum number of words per document chunk before a
            section is split further.
        chunk_overlap: Number of overlapping words between consecutive
            sub-chunks, for sections that exceed `chunk_size`.
        collection_name: Name of the Chroma collection used to store
            clinical note embeddings.
        embedding_model: Name of the FastEmbed embedding model to use.
        chroma_path: Filesystem path where the Chroma database is
            persisted.
        data_raw_dir: Directory where raw synthetic patient text files are
            written.
        data_processed_dir: Directory reserved for processed data
            artifacts.
        top_k: Number of nearest neighbors requested from Chroma per
            query.
        min_similarity_score: Minimum similarity score a retrieved chunk
            must have to be included in results.
        max_results: Maximum number of results returned to the caller
            after filtering.
        default_collection_name: Fallback Chroma collection name used
            when no explicit collection is configured.
        generation_api_key: Groq API key used for answer generation.
        generation_model: Groq model used for answer generation.
        faithfulness_api_key: Groq API key used for faithfulness
            judging.
        faithfulness_model: Groq model used for faithfulness judging.
        relevance_api_key: Groq API key used for answer relevance
            judging.
        relevance_model: Groq model used for answer relevance judging.
        temperature: Sampling temperature passed to the language model.
        max_tokens: Maximum number of tokens the language model may
            generate per response.
        llm_timeout: Maximum time, in seconds, to wait for a language
            model response before timing out.
        llm_max_retries: Maximum number of automatic retries on
            transient language model request failures, including rate
            limiting.
        llm_requests_per_minute: Maximum number of requests any single
            client is allowed to issue per minute.
        llm_retry_base_delay: Base delay, in seconds, for exponential
            backoff between retries.
        llm_retry_max_delay: Maximum delay, in seconds, allowed between
            retries.
        eval_sample_size: Maximum number of QA pairs to evaluate in a
            single evaluation run.
        graph_name: Human-readable name of the LangGraph agent graph.
        enable_evaluation: Whether the agent's evaluator node should run
            LLM-as-a-judge scoring.
        default_top_k: Default number of chunks the agent's retriever
            node requests.
        max_tool_retries: Maximum number of retry attempts for a mock
            clinical tool call before giving up.
        retry_delay: Delay, in seconds, between mock clinical tool retry
            attempts.
        default_timeout: Default timeout, in seconds, allotted to a
            mock clinical tool call.
        enable_tool_validation: Whether mock clinical tool inputs and
            outputs are validated before/after execution.
        transcription_api_key: Groq API key used for audio
            transcription. Falls back to `generation_api_key` when not
            set.
        groq_whisper_model: Name of the Groq Whisper transcription
            model to use.
        max_audio_duration: Maximum allowed audio duration, in seconds,
            for a single transcription request.
        supported_audio_formats: File extensions accepted by the audio
            loader, without leading dots.
        max_conversation_history: Maximum number of turns retained per
            conversation session before older turns are discarded.
        enable_memory: Whether conversation memory is recorded and
            supplied back to the agent.
        api_version: Version identifier reported by the REST API.
        max_upload_size: Maximum allowed size, in bytes, for an
            uploaded audio file on the voice endpoint.
        static_files_path: Filesystem path to the static frontend
            assets served alongside the API.
        enable_frontend: Whether the static frontend is mounted and
            served by the application.
        database_url: Async SQLAlchemy connection string for the
            application's PostgreSQL database.
        jwt_secret_key: Secret key used to sign and verify JWTs.
        jwt_algorithm: Signing algorithm used for JWTs.
        access_token_expire_minutes: Lifetime, in minutes, of issued
            access tokens.
        refresh_token_expire_days: Lifetime, in days, of issued refresh
            tokens.
        google_client_id: OAuth client ID used to validate Google ID
            tokens.
        google_client_secret: OAuth client secret associated with
            `google_client_id`.
        enable_rate_limiting: Whether request rate limiting is active.
        rate_limit_per_minute: Maximum requests allowed per minute per
            rate-limit key (authenticated user, or IP as fallback).
        rate_limit_per_hour: Maximum requests allowed per hour per
            rate-limit key.
        daily_request_limit: Maximum number of agent requests a single
            user may make per calendar day.
        monthly_token_limit: Maximum number of Groq tokens a single
            user may consume per calendar month.
        monthly_cost_limit: Maximum estimated Groq spend, in USD, a
            single user may incur per calendar month.
        max_request_size_mb: Maximum allowed request body size, in
            megabytes, before a request is rejected.
        trusted_hosts: Hostnames allowed in the `Host` header and as
            CORS origins.
        csp_policy: Value of the `Content-Security-Policy` response
            header.
        enable_security_headers: Whether security response headers are
            automatically applied to every response.
        enable_tracing: Whether OpenTelemetry tracing is initialized and
            FastAPI/SQLAlchemy are instrumented.
        enable_metrics: Whether Prometheus metrics are recorded.
        enable_langsmith: Whether LangSmith tracing is configured.
        langsmith_api_key: API key used to authenticate with LangSmith.
        langsmith_project: LangSmith project name traces are grouped
            under.
        otel_exporter_otlp_endpoint: OTLP collector endpoint traces are
            exported to. When empty, traces are exported to the console
            instead.
        prometheus_enabled: Whether the `/metrics` endpoint is exposed.
    """

    app_name: str = "Clinical Copilot API"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8000

    patient_count: int = 20
    chunk_size: int = 120
    chunk_overlap: int = 20
    collection_name: str = "clinical_notes"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    chroma_path: Path = Path("chroma_db")
    data_raw_dir: Path = Path("data/raw/patients")
    data_processed_dir: Path = Path("data/processed")

    top_k: int = 8
    min_similarity_score: float = 0.0
    max_results: int = 20
    default_collection_name: str = "clinical_notes"

    generation_api_key: str = ""
    generation_model: str = "llama-3.3-70b-versatile"
    faithfulness_api_key: str = ""
    faithfulness_model: str = "llama-3.1-8b-instant"
    relevance_api_key: str = ""
    relevance_model: str = "llama-3.1-8b-instant"

    temperature: float = 0.0
    max_tokens: int = 1024
    llm_timeout: float = 30.0
    llm_max_retries: int = 5
    llm_requests_per_minute: int = 20
    llm_retry_base_delay: float = 2.0
    llm_retry_max_delay: float = 60.0

    eval_sample_size: int = 10

    graph_name: str = "clinical_copilot_agent"
    enable_evaluation: bool = True
    default_top_k: int = 8

    max_tool_retries: int = 3
    retry_delay: float = 0.5
    default_timeout: float = 10.0
    enable_tool_validation: bool = True

    transcription_api_key: str = ""
    groq_whisper_model: str = "whisper-large-v3"
    max_audio_duration: float = 300.0
    supported_audio_formats: tuple[str, ...] = ("wav", "mp3", "m4a")
    max_conversation_history: int = 20
    enable_memory: bool = True

    api_version: str = "1.0.0"
    max_upload_size: int = 10_000_000
    static_files_path: Path = Path("frontend")
    enable_frontend: bool = True

    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/clinical_copilot"
    )
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    google_client_id: str = ""
    google_client_secret: str = ""

    enable_rate_limiting: bool = True
    rate_limit_per_minute: int = 30
    rate_limit_per_hour: int = 300
    daily_request_limit: int = 200
    monthly_token_limit: int = 2_000_000
    monthly_cost_limit: float = 50.0
    max_request_size_mb: float = 10.0
    trusted_hosts: tuple[str, ...] = ("*",)
    csp_policy: str = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://accounts.google.com https://apis.google.com https://*.google.com; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://accounts.google.com; "
        "img-src 'self' data: https://fastapi.tiangolo.com https://*.googleusercontent.com https://*.google.com; "
        "connect-src 'self' https://accounts.google.com https://*.googleapis.com https://*.google.com; "
        "frame-src 'self' https://accounts.google.com https://*.google.com; "
    )
    enable_security_headers: bool = True
    enable_tracing: bool = False
    enable_metrics: bool = True
    enable_langsmith: bool = False
    langsmith_api_key: str = ""
    langsmith_project: str = "clinical-copilot"
    otel_exporter_otlp_endpoint: str = ""
    prometheus_enabled: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached instance of the application settings.

    Returns:
        Settings: The cached application settings instance.
    """
    return Settings()
