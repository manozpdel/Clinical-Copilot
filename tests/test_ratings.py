"""Tests for star rating submission and validation."""

import pytest

from app.core.config import Settings
from database.base import Base
from database.models import Conversation, Query, User
from database.session import build_engine, build_session_factory
from feedback.service import FeedbackService, FeedbackValidationError, QueryNotFoundError


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
async def seeded_query(db_session):
    """Seed a user, conversation, and query."""
    user = User(email="rating-user@example.com", provider="local")
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

    return user, query


async def test_submit_rating_creates_record(db_session, seeded_query) -> None:
    """A valid rating should be created successfully."""
    user, query = seeded_query
    service = FeedbackService(db_session, Settings())

    rating = await service.submit_rating(user.id, str(query.id), 4)

    assert rating.stars == 4


async def test_submit_rating_twice_updates(db_session, seeded_query) -> None:
    """Resubmitting a rating for the same query should update, not duplicate."""
    user, query = seeded_query
    service = FeedbackService(db_session, Settings())

    first = await service.submit_rating(user.id, str(query.id), 3)
    second = await service.submit_rating(user.id, str(query.id), 5)

    assert first.id == second.id
    assert second.stars == 5


@pytest.mark.parametrize("invalid_stars", [0, 6, -1, 100])
async def test_submit_rating_rejects_out_of_range(db_session, seeded_query, invalid_stars) -> None:
    """Ratings outside 1-5 should be rejected."""
    user, query = seeded_query
    service = FeedbackService(db_session, Settings())

    with pytest.raises(FeedbackValidationError):
        await service.submit_rating(user.id, str(query.id), invalid_stars)


async def test_submit_rating_rejects_unowned_query(db_session, seeded_query) -> None:
    """A rating for a query owned by a different user should be rejected."""
    _, query = seeded_query
    service = FeedbackService(db_session, Settings())

    import uuid

    with pytest.raises(QueryNotFoundError):
        await service.submit_rating(uuid.uuid4(), str(query.id), 5)
