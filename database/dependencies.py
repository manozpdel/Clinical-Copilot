"""FastAPI dependency injection for database access.

This module is responsible ONLY for providing request-scoped database
sessions. It contains no engine construction, ORM model, or CRUD
logic.
"""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from database.session import SessionLocal


async def get_db() -> AsyncIterator[AsyncSession]:
    """Provide a request-scoped async database session.

    Yields:
        AsyncSession: An active database session, closed automatically
            when the request completes.
    """
    async with SessionLocal() as session:
        yield session
