"""Reusable database CRUD operations for the human feedback system.

This module is responsible ONLY for parameterized SQLAlchemy queries
against the Feedback, Rating, and HallucinationReport tables, plus the
ownership-checking Query lookup they depend on. It contains no
FastAPI routing or business-rule logic (see `feedback.service`).
"""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from database.models import Conversation, Query
from feedback.models import Feedback, HallucinationReport, Rating


async def get_query_owned_by_user(
    db: AsyncSession, query_id: uuid.UUID, user_id: uuid.UUID
) -> Query | None:
    """Fetch a Query only if it belongs to a conversation owned by the user.

    Args:
        db: Active async database session.
        query_id: Identifier of the query to fetch.
        user_id: Identifier of the requesting user.

    Returns:
        Query | None: The query, or None if it doesn't exist or isn't
            owned (via its conversation) by `user_id`.
    """
    result = await db.execute(
        select(Query)
        .join(Conversation, Conversation.id == Query.conversation_id)
        .where(Query.id == query_id, Conversation.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_feedback_by_user_and_query(
    db: AsyncSession, user_id: uuid.UUID, query_id: uuid.UUID
) -> Feedback | None:
    """Fetch a user's existing feedback for a specific query, if any.

    Args:
        db: Active async database session.
        user_id: Identifier of the user.
        query_id: Identifier of the query.

    Returns:
        Feedback | None: The existing feedback record, or None.
    """
    result = await db.execute(
        select(Feedback).where(Feedback.user_id == user_id, Feedback.query_id == query_id)
    )
    return result.scalar_one_or_none()


async def upsert_feedback(
    db: AsyncSession,
    user_id: uuid.UUID,
    query_id: uuid.UUID,
    is_helpful: bool | None,
    comment: str | None,
) -> Feedback:
    """Create feedback for a (user, query) pair, or update it if it exists.

    Args:
        db: Active async database session.
        user_id: Identifier of the submitting user.
        query_id: Identifier of the query.
        is_helpful: The thumbs value to set.
        comment: The comment text to set.

    Returns:
        Feedback: The created or updated feedback record.
    """
    existing = await get_feedback_by_user_and_query(db, user_id, query_id)

    if existing is not None:
        existing.is_helpful = is_helpful
        existing.comment = comment
        await db.commit()
        await db.refresh(existing)
        return existing

    feedback = Feedback(
        user_id=user_id, query_id=query_id, is_helpful=is_helpful, comment=comment
    )
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)
    return feedback


async def get_feedback_by_id(db: AsyncSession, feedback_id: uuid.UUID) -> Feedback | None:
    """Fetch a feedback record by its primary key.

    Args:
        db: Active async database session.
        feedback_id: Identifier of the feedback record.

    Returns:
        Feedback | None: The matching feedback record, or None.
    """
    return await db.get(Feedback, feedback_id)


async def update_feedback_record(
    db: AsyncSession, feedback: Feedback, is_helpful: bool | None, comment: str | None
) -> Feedback:
    """Update an existing feedback record in place.

    Args:
        db: Active async database session.
        feedback: The feedback record to update.
        is_helpful: The updated thumbs value.
        comment: The updated comment text.

    Returns:
        Feedback: The updated feedback record.
    """
    feedback.is_helpful = is_helpful
    feedback.comment = comment
    await db.commit()
    await db.refresh(feedback)
    return feedback


async def delete_feedback_record(db: AsyncSession, feedback: Feedback) -> None:
    """Delete a feedback record.

    Args:
        db: Active async database session.
        feedback: The feedback record to delete.
    """
    await db.delete(feedback)
    await db.commit()


async def list_feedback_for_user(
    db: AsyncSession, user_id: uuid.UUID, limit: int = 100
) -> list[Feedback]:
    """List a user's own feedback records, most recent first.

    Args:
        db: Active async database session.
        user_id: Identifier of the user.
        limit: Maximum number of records to return.

    Returns:
        list[Feedback]: The user's feedback records.
    """
    result = await db.execute(
        select(Feedback)
        .where(Feedback.user_id == user_id)
        .order_by(Feedback.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def list_all_feedback(db: AsyncSession) -> list[Feedback]:
    """List every feedback record, with user and query eagerly loaded.

    Intended for analytics/export, which need every record regardless
    of owner.

    Args:
        db: Active async database session.

    Returns:
        list[Feedback]: All feedback records.
    """
    result = await db.execute(
        select(Feedback).options(joinedload(Feedback.user), joinedload(Feedback.query))
    )
    return list(result.unique().scalars().all())


async def get_rating_by_user_and_query(
    db: AsyncSession, user_id: uuid.UUID, query_id: uuid.UUID
) -> Rating | None:
    """Fetch a user's existing rating for a specific query, if any.

    Args:
        db: Active async database session.
        user_id: Identifier of the user.
        query_id: Identifier of the query.

    Returns:
        Rating | None: The existing rating record, or None.
    """
    result = await db.execute(
        select(Rating).where(Rating.user_id == user_id, Rating.query_id == query_id)
    )
    return result.scalar_one_or_none()


async def upsert_rating(
    db: AsyncSession, user_id: uuid.UUID, query_id: uuid.UUID, stars: int
) -> Rating:
    """Create a rating for a (user, query) pair, or update it if it exists.

    Args:
        db: Active async database session.
        user_id: Identifier of the submitting user.
        query_id: Identifier of the query.
        stars: The rating value, from 1 to 5.

    Returns:
        Rating: The created or updated rating record.
    """
    existing = await get_rating_by_user_and_query(db, user_id, query_id)

    if existing is not None:
        existing.stars = stars
        await db.commit()
        await db.refresh(existing)
        return existing

    rating = Rating(user_id=user_id, query_id=query_id, stars=stars)
    db.add(rating)
    await db.commit()
    await db.refresh(rating)
    return rating


async def list_all_ratings(db: AsyncSession) -> list[Rating]:
    """List every rating record.

    Args:
        db: Active async database session.

    Returns:
        list[Rating]: All rating records.
    """
    result = await db.execute(select(Rating))
    return list(result.scalars().all())


async def create_hallucination_report(
    db: AsyncSession,
    user_id: uuid.UUID,
    query_id: uuid.UUID,
    reason: str,
    detail: str | None,
) -> HallucinationReport:
    """Create and persist a new hallucination/quality report.

    Args:
        db: Active async database session.
        user_id: Identifier of the reporting user.
        query_id: Identifier of the query being reported.
        reason: The reported issue category.
        detail: Optional free-text explanation.

    Returns:
        HallucinationReport: The newly created report.
    """
    report = HallucinationReport(
        user_id=user_id, query_id=query_id, reason=reason, detail=detail
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


async def list_all_hallucination_reports(db: AsyncSession) -> list[HallucinationReport]:
    """List every hallucination/quality report.

    Args:
        db: Active async database session.

    Returns:
        list[HallucinationReport]: All report records.
    """
    result = await db.execute(select(HallucinationReport))
    return list(result.scalars().all())


async def get_history_for_user(
    db: AsyncSession, user_id: uuid.UUID, limit: int = 50
) -> list[Query]:
    """List a user's own queries (across all their conversations), newest first.

    Args:
        db: Active async database session.
        user_id: Identifier of the user.
        limit: Maximum number of queries to return.

    Returns:
        list[Query]: The user's queries, most recent first.
    """
    result = await db.execute(
        select(Query)
        .join(Conversation, Conversation.id == Query.conversation_id)
        .where(Conversation.user_id == user_id)
        .order_by(Query.created_at.desc(), Query.id.desc())  # Added id as tiebreaker
        .limit(limit)
    )
    return list(result.scalars().all())


async def list_feedback_created_since(
    db: AsyncSession, since: datetime
) -> list[Feedback]:
    """List feedback created on or after a given timestamp.

    Args:
        db: Active async database session.
        since: The inclusive lower bound timestamp.

    Returns:
        list[Feedback]: Matching feedback records.
    """
    result = await db.execute(select(Feedback).where(Feedback.created_at >= since))
    return list(result.scalars().all())
