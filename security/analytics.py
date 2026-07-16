"""Usage analytics reporting.

This module is responsible ONLY for read-only aggregate queries over
`UsageLog`/`Query`/`Conversation` for reporting purposes. It contains
no quota-enforcement or write logic.
"""

from datetime import UTC, datetime, timedelta

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Conversation
from security.models import UsageLog


class UsageSummary(BaseModel):
    """Aggregated usage totals over a time period.

    Attributes:
        period_start: Start of the reporting period.
        period_end: End of the reporting period.
        request_count: Number of usage log entries in the period.
        total_tokens: Sum of tokens consumed in the period.
        total_cost_usd: Sum of estimated USD cost in the period.
        average_latency_ms: Mean latency across entries in the period.
    """

    period_start: datetime
    period_end: datetime
    request_count: int
    total_tokens: int
    total_cost_usd: float
    average_latency_ms: float


class UserActivity(BaseModel):
    """A single user's aggregated usage.

    Attributes:
        user_id: Identifier of the user.
        request_count: Number of requests made by this user.
        total_tokens: Total tokens consumed by this user.
        total_cost_usd: Total estimated USD cost incurred by this user.
    """

    user_id: str
    request_count: int
    total_tokens: int
    total_cost_usd: float


class ConversationCost(BaseModel):
    """A single conversation's aggregated cost.

    Attributes:
        conversation_id: Identifier of the conversation.
        total_cost_usd: Total estimated USD cost within this
            conversation.
        request_count: Number of requests within this conversation.
    """

    conversation_id: str
    total_cost_usd: float
    request_count: int


async def _summarize_period(db: AsyncSession, start: datetime, end: datetime) -> UsageSummary:
    """Build a UsageSummary for an arbitrary time window.

    Args:
        db: Active async database session.
        start: Inclusive start of the reporting period.
        end: Exclusive end of the reporting period.

    Returns:
        UsageSummary: The aggregated totals for the period. All
            numeric fields are zero when no usage occurred.
    """
    result = await db.execute(
        select(
            func.count(UsageLog.id),
            func.coalesce(func.sum(UsageLog.total_tokens), 0),
            func.coalesce(func.sum(UsageLog.cost_usd), 0.0),
            func.coalesce(func.avg(UsageLog.latency_ms), 0.0),
        ).where(UsageLog.created_at >= start, UsageLog.created_at < end)
    )
    request_count, total_tokens, total_cost_usd, average_latency_ms = result.one()

    return UsageSummary(
        period_start=start,
        period_end=end,
        request_count=request_count,
        total_tokens=total_tokens,
        total_cost_usd=float(total_cost_usd),
        average_latency_ms=float(average_latency_ms),
    )


async def daily_usage(db: AsyncSession, day: datetime | None = None) -> UsageSummary:
    """Summarize usage for a single calendar day.

    Args:
        db: Active async database session.
        day: Any timestamp within the target day. Defaults to now.

    Returns:
        UsageSummary: The day's aggregated usage totals.
    """
    reference = day or datetime.now(UTC)
    start = reference.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return await _summarize_period(db, start, end)


async def weekly_usage(db: AsyncSession, reference: datetime | None = None) -> UsageSummary:
    """Summarize usage for the trailing 7 days.

    Args:
        db: Active async database session.
        reference: The end of the window. Defaults to now.

    Returns:
        UsageSummary: The week's aggregated usage totals.
    """
    end = reference or datetime.now(UTC)
    start = end - timedelta(days=7)
    return await _summarize_period(db, start, end)


async def monthly_usage(db: AsyncSession, reference: datetime | None = None) -> UsageSummary:
    """Summarize usage for the current calendar month.

    Args:
        db: Active async database session.
        reference: Any timestamp within the target month. Defaults to
            now.

    Returns:
        UsageSummary: The month's aggregated usage totals.
    """
    now = reference or datetime.now(UTC)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    return await _summarize_period(db, start, next_month)


async def most_active_users(db: AsyncSession, limit: int = 10) -> list[UserActivity]:
    """List the most active users by request count.

    Args:
        db: Active async database session.
        limit: Maximum number of users to return.

    Returns:
        list[UserActivity]: Users ranked by descending request count.
    """
    result = await db.execute(
        select(
            UsageLog.user_id,
            func.count(UsageLog.id),
            func.coalesce(func.sum(UsageLog.total_tokens), 0),
            func.coalesce(func.sum(UsageLog.cost_usd), 0.0),
        )
        .group_by(UsageLog.user_id)
        .order_by(func.count(UsageLog.id).desc())
        .limit(limit)
    )

    return [
        UserActivity(
            user_id=str(user_id),
            request_count=request_count,
            total_tokens=total_tokens,
            total_cost_usd=float(total_cost_usd),
        )
        for user_id, request_count, total_tokens, total_cost_usd in result.all()
    ]


async def most_expensive_conversations(db: AsyncSession, limit: int = 10) -> list[ConversationCost]:
    """List the most expensive conversations by total estimated cost.

    Args:
        db: Active async database session.
        limit: Maximum number of conversations to return.

    Returns:
        list[ConversationCost]: Conversations ranked by descending
            total cost. Conversations with no associated usage logs
            are excluded.
    """
    result = await db.execute(
        select(
            UsageLog.conversation_id,
            func.coalesce(func.sum(UsageLog.cost_usd), 0.0),
            func.count(UsageLog.id),
        )
        .join(Conversation, Conversation.id == UsageLog.conversation_id)
        .group_by(UsageLog.conversation_id)
        .order_by(func.sum(UsageLog.cost_usd).desc())
        .limit(limit)
    )

    return [
        ConversationCost(
            conversation_id=str(conversation_id),
            total_cost_usd=float(total_cost_usd),
            request_count=request_count,
        )
        for conversation_id, total_cost_usd, request_count in result.all()
    ]


async def average_latency_ms(db: AsyncSession) -> float:
    """Compute the average latency across all recorded usage.

    Args:
        db: Active async database session.

    Returns:
        float: The average latency in milliseconds, or 0.0 if no usage
            has been recorded.
    """
    result = await db.execute(select(func.coalesce(func.avg(UsageLog.latency_ms), 0.0)))
    return float(result.scalar_one())


async def average_tokens_per_request(db: AsyncSession) -> float:
    """Compute the average total tokens consumed per request.

    Args:
        db: Active async database session.

    Returns:
        float: The average token count per request, or 0.0 if no usage
            has been recorded.
    """
    result = await db.execute(select(func.coalesce(func.avg(UsageLog.total_tokens), 0.0)))
    return float(result.scalar_one())
