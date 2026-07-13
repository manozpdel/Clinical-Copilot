"""CLI entry point that exports all feedback to CSV and JSON files on disk."""

import asyncio
from pathlib import Path

from app.core.logging import configure_logging, get_logger
from database.session import SessionLocal
from feedback.export import export_to_csv, export_to_json, gather_export_rows

CSV_PATH = Path("feedback_export.csv")
JSON_PATH = Path("feedback_export.json")


async def run_export() -> int:
    """Export all feedback to CSV and JSON files.

    Returns:
        int: Number of feedback records exported.
    """
    async with SessionLocal() as db:
        rows = await gather_export_rows(db)

    CSV_PATH.write_text(export_to_csv(rows), encoding="utf-8")
    JSON_PATH.write_text(export_to_json(rows), encoding="utf-8")
    return len(rows)


def main() -> None:
    """Run the export and print a summary."""
    configure_logging()
    logger = get_logger(__name__)
    count = asyncio.run(run_export())
    logger.info("feedback_exported", count=count)
    print(f"Exported {count} feedback record(s) to {CSV_PATH} and {JSON_PATH}.")


if __name__ == "__main__":
    main()
