"""Request/response schemas for the human feedback system.

This module is responsible ONLY for validating feedback payloads and
shaping feedback responses. It contains no routing, persistence, or
business logic.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ReportReason = Literal[
    "hallucination", "incorrect_citation", "unsafe_response", "incomplete_answer"
]


class FeedbackCreateRequest(BaseModel):
    """Request payload for submitting or updating like/dislike + comment feedback.

    Attributes:
        query_id: Identifier of the Query (question/response pair)
            this feedback is about.
        is_helpful: True for "thumbs up", False for "thumbs down", or
            None to leave only a comment.
        comment: Optional free-text feedback.
    """

    query_id: str
    is_helpful: bool | None = None
    comment: str | None = Field(default=None, max_length=10_000)


class FeedbackUpdateRequest(BaseModel):
    """Request payload for updating existing feedback.

    Attributes:
        is_helpful: The updated thumbs value, or None to leave
            unchanged... actually always applied when provided.
        comment: The updated comment text.
    """

    is_helpful: bool | None = None
    comment: str | None = Field(default=None, max_length=10_000)


class FeedbackResponse(BaseModel):
    """A single feedback record.

    Attributes:
        id: Unique feedback identifier.
        query_id: Identifier of the associated query.
        is_helpful: The submitted thumbs value, if any.
        comment: The submitted comment, if any.
        created_at: Timestamp the feedback was first submitted.
        updated_at: Timestamp the feedback was last updated.
    """

    id: str
    query_id: str
    is_helpful: bool | None
    comment: str | None
    created_at: datetime
    updated_at: datetime


class RatingCreateRequest(BaseModel):
    """Request payload for submitting or updating a star rating.

    Attributes:
        query_id: Identifier of the Query this rating is about.
        stars: The rating value, from 1 to 5 inclusive.
    """

    query_id: str
    stars: int = Field(ge=1, le=5)


class RatingResponse(BaseModel):
    """A single star rating record.

    Attributes:
        id: Unique rating identifier.
        query_id: Identifier of the associated query.
        stars: The rating value.
        created_at: Timestamp the rating was first submitted.
        updated_at: Timestamp the rating was last updated.
    """

    id: str
    query_id: str
    stars: int
    created_at: datetime
    updated_at: datetime


class HallucinationReportRequest(BaseModel):
    """Request payload for reporting an issue with a response.

    Attributes:
        query_id: Identifier of the Query this report is about.
        reason: The reported issue category.
        detail: Optional free-text explanation.
    """

    query_id: str
    reason: ReportReason
    detail: str | None = Field(default=None, max_length=10_000)


class HallucinationReportResponse(BaseModel):
    """A single hallucination/quality report record.

    Attributes:
        id: Unique report identifier.
        query_id: Identifier of the associated query.
        reason: The reported issue category.
        detail: The submitted explanation, if any.
        created_at: Timestamp the report was submitted.
    """

    id: str
    query_id: str
    reason: str
    detail: str | None
    created_at: datetime


class HistoryItem(BaseModel):
    """A single conversation turn with its associated feedback.

    Attributes:
        query_id: Identifier of the query.
        conversation_id: Identifier of the owning conversation.
        query_text: The user's original question.
        response_text: The agent's generated answer.
        citations: Formatted citation strings supporting the answer.
        evaluation: Evaluation metrics computed for the answer.
        created_at: Timestamp the query was recorded.
        feedback: The user's feedback on this response, if submitted.
        rating: The user's star rating of this response, if submitted.
    """

    query_id: str
    conversation_id: str
    query_text: str
    response_text: str
    citations: list[str]
    evaluation: dict
    created_at: datetime
    feedback: FeedbackResponse | None = None
    rating: RatingResponse | None = None


class AnalyticsResponse(BaseModel):
    """Aggregated feedback analytics.

    Attributes:
        average_rating: Mean star rating across all ratings, or None if
            no ratings exist.
        positive_percent: Percentage of thumbs-up feedback among all
            thumbs feedback.
        negative_percent: Percentage of thumbs-down feedback among all
            thumbs feedback.
        total_feedback: Total number of feedback records.
        total_ratings: Total number of rating records.
        hallucination_reports_by_reason: Count of reports per reason
            category.
        most_common_issues: Reason categories ranked by report count,
            most common first.
        daily_trend: Daily counts of feedback submissions over the
            trailing 30 days, as a list of {date, count} mappings.
    """

    average_rating: float | None
    positive_percent: float
    negative_percent: float
    total_feedback: int
    total_ratings: int
    hallucination_reports_by_reason: dict[str, int]
    most_common_issues: list[str]
    daily_trend: list[dict[str, str | int]]


class ComparisonResponse(BaseModel):
    """A side-by-side comparison of two responses.

    Attributes:
        response_a: The first response being compared.
        response_b: The second response being compared.
    """

    response_a: HistoryItem
    response_b: HistoryItem
