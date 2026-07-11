"""CLI entry point that force-resets every user's quota counters."""

import asyncio

from app.core.logging import configure_logging, get_logger
from database.crud import reset_all_quotas
from database.session import SessionLocal


async def run_reset() -> int:
    """Reset every user's quota counters.

    Returns:
        int: Number of quota records reset.
    """
    async with SessionLocal() as db:
        return await reset_all_quotas(db)


def main() -> None:
    """Reset all quotas and print how many were affected."""
    configure_logging()
    logger = get_logger(__name__)
    count = asyncio.run(run_reset())
    logger.info("quotas_reset", count=count)
    print(f"Reset {count} quota record(s).")


if __name__ == "__main__":
    main()
