"""CLI entry point for interactive RAG chat over clinical notes."""

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from llm.generator import generate_answer


def main() -> None:
    """Prompt for a question, run the RAG pipeline, and print the answer."""
    configure_logging()
    logger = get_logger(__name__)
    get_settings()

    print("Enter your question")
    question = input("> ").strip()

    if not question:
        print("No question entered. Exiting.")
        return

    result = generate_answer(question)

    print("\nAnswer\n")
    print(result.answer)
    print(f"\n(latency: {result.latency_seconds:.2f}s)")

    logger.info(
        "cli_chat_finished",
        question=question,
        latency_seconds=result.latency_seconds,
    )


if __name__ == "__main__":
    main()
