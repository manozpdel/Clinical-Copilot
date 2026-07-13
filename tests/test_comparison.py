"""Tests for response comparison."""

import pytest

from app.core.config import Settings
from database.base import Base
from database.models import Conversation, Query, User
from database.session import build_engine, build_session_factory
from feedback.comparison import ComparisonError, compare_queries


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
async def two_queries(db_session):
    """Seed a user, conversation, and two queries owned by that user."""
    user = User(email="compare-user@example.com", provider="local")
    other_user = User(email="compare-other@example.com", provider="local")
    db_session.add_all([user, other_user])
    await db_session.flush()

    conversation = Conversation(user_id=user.id)
    db_session.add(conversation)
    await db_session.flush()

    query_a = Query(
        conversation_id=conversation.id,
        query_text="q1",
        response_text="Answer A",
        citations=["cite-a"],
        evaluation={"faithfulness": 0.8},
        latency_ms=100.0,
    )
    query_b = Query(
        conversation_id=conversation.id,
        query_text="q2",
        response_text="Answer B",
        citations=["cite-b"],
        evaluation={"faithfulness": 0.9},
        latency_ms=120.0,
    )
    db_session.add_all([query_a, query_b])
    await db_session.commit()
    await db_session.refresh(query_a)
    await db_session.refresh(query_b)

    return user, other_user, query_a, query_b


async def test_compare_queries_returns_both_responses(db_session, two_queries) -> None:
    """Comparing two owned queries should return both with their content."""
    user, _, query_a, query_b = two_queries

    result = await compare_queries(db_session, user.id, str(query_a.id), str(query_b.id))

    assert result.response_a.response_text == "Answer A"
    assert result.response_b.response_text == "Answer B"


async def test_compare_queries_rejects_unowned_query(db_session, two_queries) -> None:
    """Comparing a query not owned by the requester should raise ComparisonError."""
    _, other_user, query_a, query_b = two_queries

    with pytest.raises(ComparisonError):
        await compare_queries(db_session, other_user.id, str(query_a.id), str(query_b.id))


async def test_compare_queries_rejects_invalid_id(db_session, two_queries) -> None:
    """A malformed query ID should raise ComparisonError."""
    user, _, query_a, _query_b = two_queries

    with pytest.raises(ComparisonError):
        await compare_queries(db_session, user.id, str(query_a.id), "not-a-uuid")
