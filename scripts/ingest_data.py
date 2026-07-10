"""CLI entry point for running the Clinical Copilot ingestion pipeline."""

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from ingest.ingest import run_ingestion


def main() -> None:
    """Run the ingestion pipeline and print a summary to stdout."""
    configure_logging()
    logger = get_logger(__name__)
    settings = get_settings()

    summary = run_ingestion(settings)

    separator = "-" * 34
    print(separator)
    print(f"Patients generated: {summary.patients_generated}")
    print(f"Chunks created: {summary.chunks_created}")
    print(f"Embeddings stored: {summary.embeddings_stored}")
    print(f"Collection: {summary.collection_name}")
    print(separator)

    logger.info("cli_ingestion_finished")


if __name__ == "__main__":
    main()
