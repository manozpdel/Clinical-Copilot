"""Async SQLAlchemy engine and session factory construction.

This module is responsible ONLY for building the async engine and
session factory. It contains no ORM model, CRUD, or FastAPI
dependency-injection logic; the request-scoped `get_db` dependency
lives in `database.dependencies`.
"""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings, get_settings


def build_engine(settings: Settings | None = None) -> AsyncEngine:
    """Build the async SQLAlchemy engine from application settings.

    Args:
        settings: Optional application settings override. Defaults to
            the cached global settings when not provided.

    Returns:
        AsyncEngine: The configured async database engine. Connections
            are established lazily on first use.
    """
    active_settings = settings or get_settings()
    return create_async_engine(
        active_settings.database_url,
        echo=active_settings.debug,
        pool_pre_ping=True,
    )


def build_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Build an async session factory bound to the given engine.

    Args:
        engine: The async database engine to bind sessions to.

    Returns:
        async_sessionmaker[AsyncSession]: A factory producing new async
            sessions.
    """
    return async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


engine: AsyncEngine = build_engine()
SessionLocal: async_sessionmaker[AsyncSession] = build_session_factory(engine)
