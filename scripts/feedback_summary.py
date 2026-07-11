"""CLI entry point that prints a feedback analytics summary."""

import asyncio

from app.core.logging import configure_logging, get_logger
from database.session import SessionLocal
from feedback.analytics import compute_analytics


async def print_summary() -> None:
    """Fetch and print aggregated feedback analytics."""
    async with SessionLocal() as db:
        summary = await compute_analytics(db)

    print("-" * 40)
    print(f"Average rating:     {summary.average_rating}")
    print(f"Positive feedback:  {summary.positive_percent:.1f}%")
    print(f"Negative feedback:  {summary.negative_percent:.1f}%")
    print(f"Total feedback:     {summary.total_feedback}")
    print(f"Total ratings:      {summary.total_ratings}")
    print("-" * 40)
    print("Hallucination reports by reason:")
    for reason, count in summary.hallucination_reports_by_reason.items():
        print(f"  {reason}: {count}")
    print("Most common issues:", ", ".join(summary.most_common_issues) or "none")
    print("-" * 40)


def main() -> None:
    """Run and print the feedback summary."""
    configure_logging()
    get_logger(__name__)
    asyncio.run(print_summary())


if __name__ == "__main__":
    main()
