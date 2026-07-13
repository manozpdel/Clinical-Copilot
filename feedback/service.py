"""Business logic for the human feedback system.

This module is responsible ONLY for validating and orchestrating
feedback operations (ownership checks, length limits, upsert
semantics) on top of `feedback.crud`. It contains no FastAPI routing
or raw SQL of its own.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from feedback import crud
from feedback.models import Feedback, HallucinationReport, Rating
from feedback.schemas import ReportReason


class FeedbackError(Exception):
    """Raised when a feedback operation cannot be completed."""


class FeedbackNotFoundError(FeedbackError):
    """Raised when a referenced feedback record does not exist."""


class FeedbackPermissionError(FeedbackError):
    """Raised when a user attempts to act on feedback they don't own."""


class FeedbackValidationError(FeedbackError):
    """Raised when submitted feedback content is invalid."""


class QueryNotFoundError(FeedbackError):
    """Raised when the referenced query does not exist or isn't owned by the user."""


class FeedbackService:
    """Orchestrates feedback, rating, and hallucination-report operations."""

    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        """Initialize the feedback service.

        Args:
            db: Active async database session.
            settings: Active application settings.
        """
        self._db = db
        self._settings = settings

    def _validate_comment_length(self, comment: str | None) -> None:
        """Validate a comment/detail string against the configured length limit.

        Args:
            comment: The text to validate.

        Raises:
            FeedbackValidationError: If `comment` exceeds
                `max_feedback_length`.
        """
        if comment and len(comment) > self._settings.max_feedback_length:
            raise FeedbackValidationError(
                f"Feedback text exceeds the maximum length of "
                f"{self._settings.max_feedback_length} characters."
            )

    async def _resolve_owned_query_id(
        self, user_id: uuid.UUID, query_id_str: str
    ) -> uuid.UUID:
        """Parse and verify ownership of a query ID string.

        Args:
            user_id: Identifier of the requesting user.
            query_id_str: The candidate query ID string.

        Returns:
            uuid.UUID: The validated query ID.

        Raises:
            QueryNotFoundError: If the ID is malformed, the query
                doesn't exist, or isn't owned by `user_id`.
        """
        try:
            query_id = uuid.UUID(query_id_str)
        except ValueError as error:
            raise QueryNotFoundError(f"Invalid query_id: '{query_id_str}'.") from error

        query = await crud.get_query_owned_by_user(self._db, query_id, user_id)
        if query is None:
            raise QueryNotFoundError(
                f"Query '{query_id_str}' was not found for this user."
            )
        return query_id

    async def submit_feedback(
        self,
        user_id: uuid.UUID,
        query_id_str: str,
        is_helpful: bool | None,
        comment: str | None,
    ) -> Feedback:
        """Submit (or update) thumbs-up/down and comment feedback.

        Args:
            user_id: Identifier of the submitting user.
            query_id_str: Identifier of the query being reviewed.
            is_helpful: True/False for thumbs up/down, or None.
            comment: Optional written feedback.

        Returns:
            Feedback: The created or updated feedback record.

        Raises:
            QueryNotFoundError: If the query doesn't exist or isn't
                owned by the user.
            FeedbackValidationError: If the comment is too long.
        """
        self._validate_comment_length(comment)
        query_id = await self._resolve_owned_query_id(user_id, query_id_str)
        return await crud.upsert_feedback(self._db, user_id, query_id, is_helpful, comment)

    async def update_feedback(
        self,
        user_id: uuid.UUID,
        feedback_id_str: str,
        is_helpful: bool | None,
        comment: str | None,
    ) -> Feedback:
        """Update an existing feedback record owned by the user.

        Args:
            user_id: Identifier of the requesting user.
            feedback_id_str: Identifier of the feedback record.
            is_helpful: The updated thumbs value.
            comment: The updated comment text.

        Returns:
            Feedback: The updated feedback record.

        Raises:
            FeedbackNotFoundError: If the feedback record doesn't
                exist.
            FeedbackPermissionError: If the feedback belongs to a
                different user.
            FeedbackValidationError: If the comment is too long.
        """
        self._validate_comment_length(comment)

        try:
            feedback_id = uuid.UUID(feedback_id_str)
        except ValueError as error:
            raise FeedbackNotFoundError(
                f"Invalid feedback id: '{feedback_id_str}'."
            ) from error

        feedback = await crud.get_feedback_by_id(self._db, feedback_id)
        if feedback is None:
            raise FeedbackNotFoundError(f"Feedback '{feedback_id_str}' not found.")
        if feedback.user_id != user_id:
            raise FeedbackPermissionError("You do not own this feedback record.")

        return await crud.update_feedback_record(self._db, feedback, is_helpful, comment)

    async def delete_feedback(self, user_id: uuid.UUID, feedback_id_str: str) -> None:
        """Delete a feedback record owned by the user.

        Args:
            user_id: Identifier of the requesting user.
            feedback_id_str: Identifier of the feedback record.

        Raises:
            FeedbackNotFoundError: If the feedback record doesn't
                exist.
            FeedbackPermissionError: If the feedback belongs to a
                different user.
        """
        try:
            feedback_id = uuid.UUID(feedback_id_str)
        except ValueError as error:
            raise FeedbackNotFoundError(
                f"Invalid feedback id: '{feedback_id_str}'."
            ) from error

        feedback = await crud.get_feedback_by_id(self._db, feedback_id)
        if feedback is None:
            raise FeedbackNotFoundError(f"Feedback '{feedback_id_str}' not found.")
        if feedback.user_id != user_id:
            raise FeedbackPermissionError("You do not own this feedback record.")

        await crud.delete_feedback_record(self._db, feedback)

    async def submit_rating(
        self, user_id: uuid.UUID, query_id_str: str, stars: int
    ) -> Rating:
        """Submit (or update) a 1-5 star rating for a response.

        Args:
            user_id: Identifier of the submitting user.
            query_id_str: Identifier of the query being rated.
            stars: The rating value, from 1 to 5.

        Returns:
            Rating: The created or updated rating record.

        Raises:
            QueryNotFoundError: If the query doesn't exist or isn't
                owned by the user.
            FeedbackValidationError: If `stars` is outside [1, 5].
        """
        if not 1 <= stars <= 5:
            raise FeedbackValidationError("stars must be between 1 and 5.")

        query_id = await self._resolve_owned_query_id(user_id, query_id_str)
        return await crud.upsert_rating(self._db, user_id, query_id, stars)

    async def submit_hallucination_report(
        self,
        user_id: uuid.UUID,
        query_id_str: str,
        reason: ReportReason,
        detail: str | None,
    ) -> HallucinationReport:
        """Submit a hallucination/citation/safety/completeness report.

        Args:
            user_id: Identifier of the reporting user.
            query_id_str: Identifier of the query being reported.
            reason: The reported issue category.
            detail: Optional free-text explanation.

        Returns:
            HallucinationReport: The newly created report.

        Raises:
            QueryNotFoundError: If the query doesn't exist or isn't
                owned by the user.
            FeedbackValidationError: If `detail` is too long.
        """
        self._validate_comment_length(detail)
        query_id = await self._resolve_owned_query_id(user_id, query_id_str)
        return await crud.create_hallucination_report(
            self._db, user_id, query_id, reason, detail
        )

    async def get_user_feedback_history(
        self, user_id: uuid.UUID, limit: int = 100
    ) -> list[Feedback]:
        """Fetch a user's own submitted feedback, most recent first.

        Args:
            user_id: Identifier of the user.
            limit: Maximum number of records to return.

        Returns:
            list[Feedback]: The user's feedback records.
        """
        return await crud.list_feedback_for_user(self._db, user_id, limit)
