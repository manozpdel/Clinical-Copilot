"""Reusable database CRUD operations.

This module is responsible ONLY for parameterized SQLAlchemy queries
against the User, Conversation, and Query tables. It contains no
FastAPI routing, authentication, or dependency-injection logic. No raw
SQL is used anywhere in this module.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Conversation, Query, User


def _parse_uuid(value: str) -> uuid.UUID:
    """Parse a string into a UUID, generating a new one if invalid.

    Args:
        value: The candidate UUID string.

    Returns:
        uuid.UUID: The parsed UUID, or a freshly generated one if
            `value` was not a valid UUID string.
    """
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError):
        return uuid.uuid4()


async def create_user(
    db: AsyncSession,
    email: str,
    hashed_password: str | None,
    full_name: str | None,
    provider: str,
) -> User:
    """Create and persist a new user.

    Args:
        db: Active async database session.
        email: The user's unique email address.
        hashed_password: Bcrypt password hash, or None for OAuth-only
            accounts.
        full_name: The user's display name, when known.
        provider: Authentication provider, e.g. "local" or "google".

    Returns:
        User: The newly created, persisted user.
    """
    user = User(
        email=email,
        hashed_password=hashed_password,
        full_name=full_name,
        provider=provider,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Look up a user by email address.

    Args:
        db: Active async database session.
        email: The email address to search for.

    Returns:
        User | None: The matching user, or None if not found.
    """
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: str | uuid.UUID) -> User | None:
    """Look up a user by primary key.

    Args:
        db: Active async database session.
        user_id: The user's UUID, or a string representation of it.

    Returns:
        User | None: The matching user, or None if not found or
            `user_id` is not a valid UUID.
    """
    try:
        resolved_id = (
            user_id if isinstance(user_id, uuid.UUID) else uuid.UUID(str(user_id))
        )
    except ValueError:
        return None
    return await db.get(User, resolved_id)


async def get_or_create_conversation(
    db: AsyncSession,
    user_id: uuid.UUID,
    conversation_id: str,
    title: str | None = None,
) -> Conversation:
    """Fetch a user's conversation by ID, creating it if it doesn't exist.

    If `conversation_id` refers to a conversation owned by a different
    user, a new conversation is created under the requesting user
    instead of returning the mismatched record.

    Args:
        db: Active async database session.
        user_id: Identifier of the requesting user.
        conversation_id: Candidate conversation identifier, as produced
            by the agent graph or voice pipeline.
        title: Optional title to set if a new conversation is created.

    Returns:
        Conversation: The existing or newly created conversation.
    """
    resolved_id = _parse_uuid(conversation_id)
    conversation = await db.get(Conversation, resolved_id)

    if conversation is not None and conversation.user_id == user_id:
        return conversation

    conversation = Conversation(id=resolved_id, user_id=user_id, title=title)
    db.add(conversation)
    await db.flush()
    return conversation


async def create_query_record(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    query_text: str,
    response_text: str,
    citations: list[str],
    evaluation: dict,
    latency_ms: float,
) -> Query:
    """Create and persist a new query record within a conversation.

    Args:
        db: Active async database session.
        conversation_id: Identifier of the owning conversation.
        query_text: The user's question.
        response_text: The agent's generated answer.
        citations: Formatted citation strings supporting the answer.
        evaluation: Evaluation metrics computed for the answer.
        latency_ms: Wall-clock time, in milliseconds, taken to answer.

    Returns:
        Query: The newly created, persisted query record.
    """
    query = Query(
        conversation_id=conversation_id,
        query_text=query_text,
        response_text=response_text,
        citations=citations,
        evaluation=evaluation,
        latency_ms=latency_ms,
    )
    db.add(query)
    await db.commit()
    await db.refresh(query)
    return query


async def record_query_turn(
    db: AsyncSession,
    user_id: uuid.UUID,
    conversation_id: str,
    query_text: str,
    response_text: str,
    citations: list[str],
    evaluation: dict,
    latency_ms: float,
) -> Conversation:
    """Persist one full question/answer turn under a user's conversation.

    Args:
        db: Active async database session.
        user_id: Identifier of the requesting user.
        conversation_id: Candidate conversation identifier from the
            agent graph or voice pipeline.
        query_text: The user's question.
        response_text: The agent's generated answer.
        citations: Formatted citation strings supporting the answer.
        evaluation: Evaluation metrics computed for the answer.
        latency_ms: Wall-clock time, in milliseconds, taken to answer.

    Returns:
        Conversation: The conversation the turn was recorded under.
    """
    conversation = await get_or_create_conversation(db, user_id, conversation_id)
    await create_query_record(
        db,
        conversation_id=conversation.id,
        query_text=query_text,
        response_text=response_text,
        citations=citations,
        evaluation=evaluation,
        latency_ms=latency_ms,
    )
    return conversation


async def list_queries_for_conversation(
    db: AsyncSession, conversation_id: uuid.UUID
) -> list[Query]:
    """List all queries recorded within a conversation, oldest first.

    Args:
        db: Active async database session.
        conversation_id: Identifier of the conversation to list.

    Returns:
        list[Query]: The conversation's queries, ordered by creation
            time.
    """
    result = await db.execute(
        select(Query)
        .where(Query.conversation_id == conversation_id)
        .order_by(Query.created_at.asc())
    )
    return list(result.scalars().all())
