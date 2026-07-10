"""Development utility that creates all database tables directly.

Intended for quick local setup. Production and any environment that
needs versioned schema history should use Alembic migrations
(`alembic upgrade head`) instead.
"""

import asyncio

from app.core.logging import configure_logging, get_logger
from database.base import Base
from database.models import Conversation, Query, User  # noqa: F401 (register tables)
from database.session import engine


async def create_all_tables() -> None:
    """Create all ORM-mapped tables in the configured database."""
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


def main() -> None:
    """Create all database tables and report success."""
    configure_logging()
    logger = get_logger(__name__)
    asyncio.run(create_all_tables())
    logger.info("database_tables_created")
    print("Database tables created successfully.")


if __name__ == "__main__":
    main()
