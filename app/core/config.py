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
            LLM-as-a-judge scoring. When disabled, the evaluator node
            still runs but skips the LLM call.
        default_top_k: Default number of chunks the agent's retriever
            node requests, independent of the standalone RAG CLI's
            `top_k` setting.
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