"""Tests for usage analytics aggregation."""

from datetime import UTC, datetime

import pytest

from app.core.config import Settings
from database.base import Base
from database.models import Conversation, User
from database.session import build_engine, build_session_factory
from security.analytics import (
    average_latency_ms,
    average_tokens_per_request,
    daily_usage,
    most_active_users,
    most_expensive_conversations,
)
from security.models import UsageLog


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
async def seeded_usage(db_session):
    """Seed a user, conversation, and two usage log entries."""
    user = User(email="analytics-user@example.com", provider="local")
    db_session.add(user)
    await db_session.flush()

    conversation = Conversation(user_id=user.id, title="Test conversation")
    db_session.add(conversation)
    await db_session.flush()

    log_one = UsageLog(
        user_id=user.id,
        conversation_id=conversation.id,
        model="llama-3.3-70b-versatile",
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        cost_usd=0.01,
        latency_ms=500.0,
        created_at=datetime.now(UTC),
    )
    log_two = UsageLog(
        user_id=user.id,
        conversation_id=conversation.id,
        model="llama-3.3-70b-versatile",
        prompt_tokens=200,
        completion_tokens=100,
        total_tokens=300,
        cost_usd=0.02,
        latency_ms=700.0,
        created_at=datetime.now(UTC),
    )
    db_session.add_all([log_one, log_two])
    await db_session.commit()

    return user, conversation


async def test_daily_usage_aggregates_todays_logs(db_session, seeded_usage) -> None:
    """Today's usage summary should include both seeded logs."""
    summary = await daily_usage(db_session)

    assert summary.request_count == 2
    assert summary.total_tokens == 450
    assert summary.total_cost_usd == pytest.approx(0.03)


async def test_most_active_users_ranks_by_request_count(db_session, seeded_usage) -> None:
    """The seeded user should appear with the correct request count."""
    user, _ = seeded_usage

    results = await most_active_users(db_session, limit=5)

    assert len(results) == 1
    assert results[0].user_id == str(user.id)
    assert results[0].request_count == 2


async def test_most_expensive_conversations_ranks_by_cost(db_session, seeded_usage) -> None:
    """The seeded conversation should appear with the correct total cost."""
    _, conversation = seeded_usage

    results = await most_expensive_conversations(db_session, limit=5)

    assert len(results) == 1
    assert results[0].conversation_id == str(conversation.id)
    assert results[0].total_cost_usd == pytest.approx(0.03)


async def test_average_latency_ms_computes_mean(db_session, seeded_usage) -> None:
    """Average latency should be the mean of the seeded entries."""
    average = await average_latency_ms(db_session)

    assert average == pytest.approx(600.0)


async def test_average_tokens_per_request_computes_mean(db_session, seeded_usage) -> None:
    """Average tokens should be the mean of the seeded entries."""
    average = await average_tokens_per_request(db_session)

    assert average == pytest.approx(225.0)
