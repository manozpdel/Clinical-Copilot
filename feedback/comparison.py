"""Response comparison utilities.

This module is responsible ONLY for loading two queries (with their
feedback/ratings) and composing them into a side-by-side comparison.
It contains no analytics or persistence-write logic.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from feedback.crud import (
    get_feedback_by_user_and_query,
    get_query_owned_by_user,
    get_rating_by_user_and_query,
)
from feedback.schemas import ComparisonResponse, FeedbackResponse, HistoryItem, RatingResponse


class ComparisonError(Exception):
    """Raised when one or both queries being compared cannot be loaded."""


def _to_feedback_response(feedback) -> FeedbackResponse | None:
    """Convert an ORM Feedback record into its response schema, if present.

    Args:
        feedback: The ORM Feedback instance, or None.

    Returns:
        FeedbackResponse | None: The converted schema, or None.
    """
    if feedback is None:
        return None
    return FeedbackResponse(
        id=str(feedback.id),
        query_id=str(feedback.query_id),
        is_helpful=feedback.is_helpful,
        comment=feedback.comment,
        created_at=feedback.created_at,
        updated_at=feedback.updated_at,
    )


def _to_rating_response(rating) -> RatingResponse | None:
    """Convert an ORM Rating record into its response schema, if present.

    Args:
        rating: The ORM Rating instance, or None.

    Returns:
        RatingResponse | None: The converted schema, or None.
    """
    if rating is None:
        return None
    return RatingResponse(
        id=str(rating.id),
        query_id=str(rating.query_id),
        stars=rating.stars,
        created_at=rating.created_at,
        updated_at=rating.updated_at,
    )


async def _build_history_item(
    db: AsyncSession, user_id: uuid.UUID, query_id: uuid.UUID
) -> HistoryItem:
    """Build a HistoryItem for a single query owned by the user.

    Args:
        db: Active async database session.
        user_id: Identifier of the requesting (owning) user.
        query_id: Identifier of the query to load.

    Returns:
        HistoryItem: The query with its feedback and rating attached.

    Raises:
        ComparisonError: If the query doesn't exist or isn't owned by
            `user_id`.
    """
    query = await get_query_owned_by_user(db, query_id, user_id)
    if query is None:
        raise ComparisonError(f"Query '{query_id}' was not found for this user.")

    feedback = await get_feedback_by_user_and_query(db, user_id, query_id)
    rating = await get_rating_by_user_and_query(db, user_id, query_id)

    return HistoryItem(
        query_id=str(query.id),
        conversation_id=str(query.conversation_id),
        query_text=query.query_text,
        response_text=query.response_text,
        citations=query.citations,
        evaluation=query.evaluation,
        created_at=query.created_at,
        feedback=_to_feedback_response(feedback),
        rating=_to_rating_response(rating),
    )


async def compare_queries(
    db: AsyncSession, user_id: uuid.UUID, query_id_a_str: str, query_id_b_str: str
) -> ComparisonResponse:
    """Load two queries owned by the user and compose a side-by-side comparison.

    Args:
        db: Active async database session.
        user_id: Identifier of the requesting user.
        query_id_a_str: Identifier of the first query.
        query_id_b_str: Identifier of the second query.

    Returns:
        ComparisonResponse: Both responses, each with their citations,
            evaluation, timestamp, feedback, and rating.

    Raises:
        ComparisonError: If either ID is malformed, or either query
            doesn't exist / isn't owned by the user.
    """
    try:
        query_id_a = uuid.UUID(query_id_a_str)
        query_id_b = uuid.UUID(query_id_b_str)
    except ValueError as error:
        raise ComparisonError("One or both query IDs are invalid.") from error

    response_a = await _build_history_item(db, user_id, query_id_a)
    response_b = await _build_history_item(db, user_id, query_id_b)

    return ComparisonResponse(response_a=response_a, response_b=response_b)
