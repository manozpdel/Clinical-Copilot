"""CLI entry point for interactive semantic search over clinical notes."""

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from rag.formatter import format_results
from rag.search import search


def main() -> None:
    """Prompt for a query, run retrieval, and print formatted results."""
    configure_logging()
    logger = get_logger(__name__)
    get_settings()

    print("Enter your query")
    query = input("> ").strip()

    if not query:
        print("No query entered. Exiting.")
        return

    response = search(query)

    print("\nTop Results\n")
    print(format_results(response.results))

    logger.info("cli_query_finished", query=query, result_count=len(response.results))


if __name__ == "__main__":
    main()
