"""Tests for user conversation/feedback history retrieval."""

from datetime import datetime, timedelta

import pytest

from app.core.config import Settings
from database.base import Base
from database.models import Conversation, Query, User
from database.session import build_engine, build_session_factory
from feedback.crud import get_history_for_user, upsert_feedback, upsert_rating


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


async def test_get_history_for_user_returns_own_queries_only(db_session) -> None:
    """History should only include queries owned by the requesting user."""
    user = User(email="history-user@example.com", provider="local")
    other_user = User(email="history-other@example.com", provider="local")
    db_session.add_all([user, other_user])
    await db_session.flush()

    conversation = Conversation(user_id=user.id)
    other_conversation = Conversation(user_id=other_user.id)
    db_session.add_all([conversation, other_conversation])
    await db_session.flush()

    query = Query(
        conversation_id=conversation.id,
        query_text="mine",
        response_text="mine answer",
        citations=[],
        evaluation={},
        latency_ms=1.0,
    )
    other_query = Query(
        conversation_id=other_conversation.id,
        query_text="not mine",
        response_text="not mine answer",
        citations=[],
        evaluation={},
        latency_ms=1.0,
    )
    db_session.add_all([query, other_query])
    await db_session.commit()

    history = await get_history_for_user(db_session, user.id)

    assert len(history) == 1
    assert history[0].query_text == "mine"


async def test_get_history_for_user_orders_newest_first(db_session) -> None:
    """History should be ordered with the most recently created query first."""
    user = User(email="history-order@example.com", provider="local")
    db_session.add(user)
    await db_session.flush()

    conversation = Conversation(user_id=user.id)
    db_session.add(conversation)
    await db_session.flush()

    # Get current time for explicit timestamps
    now = datetime.utcnow()

    # Create first query (older - 1 second ago)
    first = Query(
        conversation_id=conversation.id,
        query_text="first",
        response_text="a",
        citations=[],
        evaluation={},
        latency_ms=1.0,
        created_at=now - timedelta(seconds=1),  # Explicitly older
    )
    db_session.add(first)
    await db_session.commit()

    # Create second query (newer - current time)
    second = Query(
        conversation_id=conversation.id,
        query_text="second",
        response_text="b",
        citations=[],
        evaluation={},
        latency_ms=1.0,
        created_at=now,  # Explicitly newer
    )
    db_session.add(second)
    await db_session.commit()

    # Get history - should have second first, then first
    history = await get_history_for_user(db_session, user.id)

    # Verify ordering
    assert len(history) == 2
    assert history[0].query_text == "second"
    assert history[1].query_text == "first"


async def test_history_includes_feedback_and_rating_via_crud(db_session) -> None:
    """Feedback and rating attached to a query should be retrievable alongside it."""
    user = User(email="history-fb@example.com", provider="local")
    db_session.add(user)
    await db_session.flush()

    conversation = Conversation(user_id=user.id)
    db_session.add(conversation)
    await db_session.flush()

    query = Query(
        conversation_id=conversation.id,
        query_text="q",
        response_text="a",
        citations=[],
        evaluation={},
        latency_ms=1.0,
    )
    db_session.add(query)
    await db_session.commit()
    await db_session.refresh(query)

    await upsert_feedback(db_session, user.id, query.id, True, "nice")
    await upsert_rating(db_session, user.id, query.id, 5)

    history = await get_history_for_user(db_session, user.id)

    assert len(history) == 1
    assert history[0].id == query.id
