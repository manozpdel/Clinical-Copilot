"""CLI entry point for running the RAG evaluation harness.

Evaluates a bounded sample of the generated QA dataset, using the
proactive rate limiter and retry logic built into GroqClient to stay
within free-tier API limits.
"""

from pathlib import Path

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from evaluation.dataset import generate_qa_dataset
from evaluation.evaluator import run_evaluation
from evaluation.report import print_summary, write_csv_report


def main() -> None:
    """Generate a QA dataset, run evaluation on a sample, and produce a report."""
    configure_logging()
    logger = get_logger(__name__)
    settings = get_settings()

    dataset = generate_qa_dataset(settings)
    sample = dataset[: settings.eval_sample_size]
    logger.info(
        "qa_dataset_generated",
        item_count=len(dataset),
        sample_size=len(sample),
    )
    print(f"Evaluating {len(sample)} of {len(dataset)} generated questions.")

    results, summary = run_evaluation(sample, settings=settings)
    print_summary(summary)

    output_path = Path("evaluation_report.csv")
    write_csv_report(results, output_path)
    logger.info("evaluation_report_written", path=str(output_path))


if __name__ == "__main__":
    main()
