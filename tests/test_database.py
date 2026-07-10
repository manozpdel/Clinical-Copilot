"""Tests for the async database engine, session, and dependency."""

import pytest
import sqlalchemy as sa

from app.core.config import Settings
from database.base import Base
from database.models import Conversation, Query, User  # noqa: F401 (register tables)
from database.session import build_engine, build_session_factory


@pytest.fixture
async def sqlite_session_factory():
    """Provide a fresh in-memory SQLite session factory with tables created."""
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:")
    engine = build_engine(settings)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    factory = build_session_factory(engine)
    yield factory

    await engine.dispose()


async def test_session_factory_produces_working_session(sqlite_session_factory) -> None:
    """A session from the factory should be able to execute a query."""
    async with sqlite_session_factory() as session:
        result = await session.execute(sa.text("SELECT 1"))
        assert result.scalar_one() == 1


async def test_build_engine_uses_provided_settings() -> None:
    """build_engine should honor an explicit settings override."""
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:")

    engine = build_engine(settings)

    assert str(engine.url).startswith("sqlite+aiosqlite")
    await engine.dispose()
