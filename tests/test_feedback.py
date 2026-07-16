"""Tests for feedback CRUD/service (thumbs + comments)."""

import pytest

from app.core.config import Settings
from database.base import Base
from database.models import Conversation, Query, User
from database.session import build_engine, build_session_factory
from feedback.service import (
    FeedbackNotFoundError,
    FeedbackPermissionError,
    FeedbackService,
    FeedbackValidationError,
    QueryNotFoundError,
)


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
async def seeded(db_session):
    """Seed a user, a second user, a conversation, and a query."""
    user = User(email="fb-user@example.com", provider="local")
    other_user = User(email="fb-other@example.com", provider="local")
    db_session.add_all([user, other_user])
    await db_session.flush()

    conversation = Conversation(user_id=user.id, title="Test")
    db_session.add(conversation)
    await db_session.flush()

    query = Query(
        conversation_id=conversation.id,
        query_text="What medications is patient_001 taking?",
        response_text="Metformin 500mg twice daily.",
        citations=["[Citation: Patient patient_001, Chunk c1, patient_001.txt]"],
        evaluation={"faithfulness": 0.9},
        latency_ms=120.0,
    )
    db_session.add(query)
    await db_session.commit()
    await db_session.refresh(query)

    return user, other_user, query


async def test_submit_feedback_creates_record(db_session, seeded) -> None:
    """Submitting feedback for the first time should create a new record."""
    user, _, query = seeded
    service = FeedbackService(db_session, Settings())

    feedback = await service.submit_feedback(user.id, str(query.id), True, "Great answer")

    assert feedback.is_helpful is True
    assert feedback.comment == "Great answer"


async def test_submit_feedback_twice_upserts(db_session, seeded) -> None:
    """Resubmitting feedback for the same query should update, not duplicate."""
    user, _, query = seeded
    service = FeedbackService(db_session, Settings())

    first = await service.submit_feedback(user.id, str(query.id), True, "Good")
    second = await service.submit_feedback(user.id, str(query.id), False, "Actually not great")

    assert first.id == second.id
    assert second.is_helpful is False
    assert second.comment == "Actually not great"


async def test_submit_feedback_rejects_unowned_query(db_session, seeded) -> None:
    """A user cannot submit feedback for a query they don't own."""
    _, other_user, query = seeded
    service = FeedbackService(db_session, Settings())

    with pytest.raises(QueryNotFoundError):
        await service.submit_feedback(other_user.id, str(query.id), True, None)


async def test_submit_feedback_rejects_overlong_comment(db_session, seeded) -> None:
    """A comment exceeding the configured max length should be rejected."""
    user, _, query = seeded
    service = FeedbackService(db_session, Settings(max_feedback_length=10))

    with pytest.raises(
        FeedbackValidationError, match="Feedback text exceeds the maximum length of 10 characters."
    ):
        await service.submit_feedback(user.id, str(query.id), True, "x" * 20)


async def test_update_feedback_by_owner_succeeds(db_session, seeded) -> None:
    """The owning user should be able to update their feedback."""
    user, _, query = seeded
    service = FeedbackService(db_session, Settings())
    feedback = await service.submit_feedback(user.id, str(query.id), True, "Initial")

    updated = await service.update_feedback(user.id, str(feedback.id), False, "Changed my mind")

    assert updated.is_helpful is False
    assert updated.comment == "Changed my mind"


async def test_update_feedback_by_non_owner_raises(db_session, seeded) -> None:
    """A non-owning user should not be able to update someone else's feedback."""
    user, other_user, query = seeded
    service = FeedbackService(db_session, Settings())
    feedback = await service.submit_feedback(user.id, str(query.id), True, "Initial")

    with pytest.raises(FeedbackPermissionError):
        await service.update_feedback(other_user.id, str(feedback.id), False, "Hijack")


async def test_delete_feedback_by_owner_succeeds(db_session, seeded) -> None:
    """The owning user should be able to delete their feedback."""
    user, _, query = seeded
    service = FeedbackService(db_session, Settings())
    feedback = await service.submit_feedback(user.id, str(query.id), True, "Initial")

    await service.delete_feedback(user.id, str(feedback.id))

    from feedback.crud import get_feedback_by_id

    assert await get_feedback_by_id(db_session, feedback.id) is None


async def test_delete_nonexistent_feedback_raises(db_session, seeded) -> None:
    """Deleting a nonexistent feedback ID should raise FeedbackNotFoundError."""
    user, _, _query = seeded
    service = FeedbackService(db_session, Settings())

    import uuid

    with pytest.raises(FeedbackNotFoundError):
        await service.delete_feedback(user.id, str(uuid.uuid4()))
