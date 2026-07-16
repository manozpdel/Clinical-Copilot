"""SQLAlchemy ORM models for usage tracking and quota enforcement.

This module is responsible ONLY for defining the UsageLog and Quota
tables. It contains no engine, session, CRUD, quota-enforcement, or
cost-calculation logic.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base
from database.models import GUID


class UsageLog(Base):
    """A single record of Groq usage incurred by one agent call.

    Attributes:
        id: Unique usage log identifier.
        user_id: Identifier of the user who triggered the call.
        conversation_id: Identifier of the associated conversation, if
            known.
        model: Name of the Groq model used.
        prompt_tokens: Estimated or reported prompt token count.
        completion_tokens: Estimated or reported completion token
            count.
        total_tokens: Sum of prompt and completion tokens.
        cost_usd: Estimated USD cost of the call.
        latency_ms: Wall-clock time, in milliseconds, taken by the call.
        created_at: Timestamp the usage was recorded.
    """

    __tablename__ = "usage_logs"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Quota(Base):
    """A user's rolling daily/monthly usage quota counters.

    Attributes:
        id: Unique quota record identifier.
        user_id: Identifier of the owning user (one quota per user).
        daily_request_count: Number of agent requests made so far in
            the current day.
        daily_reset_date: The date `daily_request_count` was last reset.
        monthly_token_count: Number of tokens consumed so far in the
            current month.
        monthly_cost_usd: Estimated USD spend so far in the current
            month.
        monthly_reset_month: The first day of the month
            `monthly_token_count`/`monthly_cost_usd` were last reset.
    """

    __tablename__ = "quotas"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    daily_request_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    daily_reset_date: Mapped[date] = mapped_column(Date, nullable=False)
    monthly_token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    monthly_cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    monthly_reset_month: Mapped[date] = mapped_column(Date, nullable=False)
