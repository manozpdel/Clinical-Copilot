"""Tests for the User, Conversation, and Query ORM models and relationships."""

import uuid

import pytest
from sqlalchemy import select

from app.core.config import Settings
from database.base import Base
from database.models import Conversation, Query, User
from database.session import build_engine, build_session_factory


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


async def test_create_user_and_conversation_relationship(db_session) -> None:
    """A conversation should be reachable from its owning user."""
    user = User(email="alice@example.com", provider="local")
    db_session.add(user)
    await db_session.flush()

    conversation = Conversation(user_id=user.id, title="First chat")
    db_session.add(conversation)
    await db_session.commit()
    await db_session.refresh(user)

    result = await db_session.execute(
        select(Conversation).where(Conversation.user_id == user.id)
    )
    fetched = result.scalar_one()

    assert fetched.title == "First chat"
    assert fetched.user_id == user.id


async def test_query_belongs_to_conversation(db_session) -> None:
    """A query should be reachable from its owning conversation."""
    user = User(email="bob@example.com", provider="local")
    db_session.add(user)
    await db_session.flush()

    conversation = Conversation(user_id=user.id)
    db_session.add(conversation)
    await db_session.flush()

    query = Query(
        conversation_id=conversation.id,
        query_text="What medications is P0005 taking?",
        response_text="Atorvastatin 20mg nightly.",
        citations=["[Citation: Patient P0005, Chunk tool_ehr_P0005, mock_ehr_api]"],
        evaluation={"faithfulness": 0.9},
        latency_ms=120.5,
    )
    db_session.add(query)
    await db_session.commit()

    result = await db_session.execute(
        select(Query).where(Query.conversation_id == conversation.id)
    )
    fetched = result.scalar_one()

    assert fetched.query_text == "What medications is P0005 taking?"
    assert fetched.citations == [
        "[Citation: Patient P0005, Chunk tool_ehr_P0005, mock_ehr_api]"
    ]
    assert fetched.evaluation == {"faithfulness": 0.9}


async def test_guid_round_trips_uuid_values(db_session) -> None:
    """A user's ID should round-trip as a real uuid.UUID instance."""
    user = User(email="carol@example.com", provider="local")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    assert isinstance(user.id, uuid.UUID)
