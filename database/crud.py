"""Reusable database CRUD operations.

This module is responsible ONLY for parameterized SQLAlchemy queries
against the User, Conversation, Query, UsageLog, and Quota tables. It
contains no FastAPI routing, authentication, quota-enforcement, or
cost-calculation logic. No raw SQL is used anywhere in this module.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Conversation, Query, User
from security.models import Quota, UsageLog


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
        resolved_id = user_id if isinstance(user_id, uuid.UUID) else uuid.UUID(str(user_id))
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
) -> tuple[Conversation, Query]:
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
        tuple[Conversation, Query]: The conversation the turn was
            recorded under, and the newly persisted query record
            (returned so callers, e.g. the API layer, can expose its
            ID for attaching feedback/ratings).
    """
    conversation = await get_or_create_conversation(db, user_id, conversation_id)
    query = await create_query_record(
        db,
        conversation_id=conversation.id,
        query_text=query_text,
        response_text=response_text,
        citations=citations,
        evaluation=evaluation,
        latency_ms=latency_ms,
    )
    return conversation, query


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


async def create_usage_log(
    db: AsyncSession,
    user_id: uuid.UUID,
    conversation_id: uuid.UUID | None,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    cost_usd: float,
    latency_ms: float,
) -> UsageLog:
    """Create and persist a usage log entry for a single agent call.

    Args:
        db: Active async database session.
        user_id: Identifier of the requesting user.
        conversation_id: Identifier of the associated conversation, if
            known.
        model: Name of the Groq model used.
        prompt_tokens: Estimated or reported prompt token count.
        completion_tokens: Estimated or reported completion token
            count.
        cost_usd: Estimated USD cost of the call.
        latency_ms: Wall-clock time, in milliseconds, taken by the call.

    Returns:
        UsageLog: The newly created, persisted usage log entry.
    """
    log = UsageLog(
        user_id=user_id,
        conversation_id=conversation_id,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


async def get_or_create_quota(db: AsyncSession, user_id: uuid.UUID) -> Quota:
    """Fetch a user's quota record, creating a fresh one if absent.

    Args:
        db: Active async database session.
        user_id: Identifier of the user.

    Returns:
        Quota: The existing or newly created quota record.
    """
    result = await db.execute(select(Quota).where(Quota.user_id == user_id))
    quota = result.scalar_one_or_none()

    if quota is not None:
        return quota

    today = datetime.now(UTC).date()
    quota = Quota(
        user_id=user_id,
        daily_request_count=0,
        daily_reset_date=today,
        monthly_token_count=0,
        monthly_cost_usd=0.0,
        monthly_reset_month=today.replace(day=1),
    )
    db.add(quota)
    await db.commit()
    await db.refresh(quota)
    return quota


async def reset_quota_periods(db: AsyncSession, quota: Quota) -> Quota:
    """Reset a quota's daily/monthly counters if their periods have elapsed.

    Args:
        db: Active async database session.
        quota: The quota record to check and potentially reset.

    Returns:
        Quota: The quota record, reset in place if its periods elapsed.
    """
    today = datetime.now(UTC).date()

    if quota.daily_reset_date < today:
        quota.daily_request_count = 0
        quota.daily_reset_date = today

    current_month = today.replace(day=1)
    if quota.monthly_reset_month < current_month:
        quota.monthly_token_count = 0
        quota.monthly_cost_usd = 0.0
        quota.monthly_reset_month = current_month

    await db.commit()
    await db.refresh(quota)
    return quota


async def increment_quota_usage(
    db: AsyncSession, quota: Quota, tokens: int, cost_usd: float
) -> Quota:
    """Increment a quota's request/token/cost counters after a call.

    Args:
        db: Active async database session.
        quota: The quota record to increment.
        tokens: Number of tokens consumed by the call.
        cost_usd: Estimated USD cost of the call.

    Returns:
        Quota: The updated quota record.
    """
    quota.daily_request_count += 1
    quota.monthly_token_count += tokens
    quota.monthly_cost_usd += cost_usd

    await db.commit()
    await db.refresh(quota)
    return quota


async def reset_all_quotas(db: AsyncSession) -> int:
    """Force-reset every user's quota counters, regardless of period.

    Intended for administrative use (e.g. `scripts/reset_quotas.py`).

    Args:
        db: Active async database session.

    Returns:
        int: Number of quota records reset.
    """
    result = await db.execute(select(Quota))
    quotas = list(result.scalars().all())

    today = datetime.now(UTC).date()
    for quota in quotas:
        quota.daily_request_count = 0
        quota.daily_reset_date = today
        quota.monthly_token_count = 0
        quota.monthly_cost_usd = 0.0
        quota.monthly_reset_month = today.replace(day=1)

    await db.commit()
    return len(quotas)
