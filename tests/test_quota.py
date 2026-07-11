"""Tests for per-user quota enforcement."""

import pytest

from app.core.config import Settings
from database.base import Base
from database.crud import get_or_create_quota, increment_quota_usage
from database.models import User
from database.session import build_engine, build_session_factory
from security.quota import QuotaExceededError, check_quota_before_request


@pytest.fixture
async def db_session():
    """Provide a fresh in-memory SQLite session with tables created."""
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:")
    engine = build_engine(settings)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    factory = build_session_factory(engine)
    async with factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def test_user(db_session):
    """Persist and return a test user."""
    user = User(email="quota-user@example.com", provider="local")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def test_quota_allows_request_within_limits(db_session, test_user) -> None:
    """A user with no prior usage should pass the quota check."""
    settings = Settings(daily_request_limit=10, monthly_token_limit=1000, monthly_cost_limit=10.0)

    quota = await check_quota_before_request(db_session, test_user.id, settings)

    assert quota.daily_request_count == 0


async def test_quota_rejects_when_daily_limit_reached(db_session, test_user) -> None:
    """A user at the daily request limit should be rejected."""
    settings = Settings(daily_request_limit=1, monthly_token_limit=1000, monthly_cost_limit=10.0)

    quota = await get_or_create_quota(db_session, test_user.id)
    await increment_quota_usage(db_session, quota, tokens=10, cost_usd=0.01)

    with pytest.raises(QuotaExceededError):
        await check_quota_before_request(db_session, test_user.id, settings)


async def test_quota_rejects_when_monthly_cost_limit_reached(db_session, test_user) -> None:
    """A user at the monthly cost limit should be rejected."""
    settings = Settings(daily_request_limit=100, monthly_token_limit=1_000_000, monthly_cost_limit=1.0)

    quota = await get_or_create_quota(db_session, test_user.id)
    await increment_quota_usage(db_session, quota, tokens=10, cost_usd=1.0)

    with pytest.raises(QuotaExceededError):
        await check_quota_before_request(db_session, test_user.id, settings)
