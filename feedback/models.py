"""SQLAlchemy ORM models for the human feedback system.

This module is responsible ONLY for defining the Feedback, Rating, and
HallucinationReport tables and their relationships to User and Query.
It contains no CRUD, business-logic, or FastAPI routing logic.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base
from database.models import GUID, Query, User


class Feedback(Base):
    """A user's thumbs-up/down and optional written comment on a response.

    One row per (user, query); resubmitting updates the existing row
    rather than creating a duplicate.

    Attributes:
        id: Unique feedback identifier.
        user_id: Identifier of the user who submitted the feedback.
        query_id: Identifier of the Query (question/response pair) the
            feedback is about.
        is_helpful: True for a "thumbs up", False for "thumbs down",
            or None if only a comment was left.
        comment: Optional free-text feedback.
        created_at: Timestamp the feedback was first submitted.
        updated_at: Timestamp the feedback was last updated.
        user: The submitting user.
        query: The query/response the feedback is about.
    """

    __tablename__ = "feedback"
    __table_args__ = (
        UniqueConstraint("user_id", "query_id", name="uq_feedback_user_query"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    query_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("queries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    is_helpful: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship(User)
    query: Mapped["Query"] = relationship(Query)


class Rating(Base):
    """A user's 1-5 star rating of a response.

    One rating per (user, query); resubmitting updates the existing
    rating rather than creating a duplicate.

    Attributes:
        id: Unique rating identifier.
        user_id: Identifier of the user who submitted the rating.
        query_id: Identifier of the Query the rating is about.
        stars: The rating value, from 1 to 5 inclusive.
        created_at: Timestamp the rating was first submitted.
        updated_at: Timestamp the rating was last updated.
        user: The submitting user.
        query: The query/response the rating is about.
    """

    __tablename__ = "ratings"
    __table_args__ = (
        UniqueConstraint("user_id", "query_id", name="uq_rating_user_query"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    query_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("queries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stars: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship(User)
    query: Mapped["Query"] = relationship(Query)


class HallucinationReport(Base):
    """A user's report that a response has a quality or safety issue.

    Attributes:
        id: Unique report identifier.
        user_id: Identifier of the reporting user.
        query_id: Identifier of the Query the report is about.
        reason: The reported issue category (hallucination,
            incorrect_citation, unsafe_response, or incomplete_answer).
        detail: Optional free-text explanation.
        created_at: Timestamp the report was submitted.
        user: The reporting user.
        query: The query/response the report is about.
    """

    __tablename__ = "hallucination_reports"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    query_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("queries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reason: Mapped[str] = mapped_column(String(50), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(User)
    query: Mapped["Query"] = relationship(Query)
