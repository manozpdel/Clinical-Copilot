"""Feedback analytics aggregation.

This module is responsible ONLY for computing read-only analytics over
feedback, ratings, and hallucination reports. It contains no
persistence-write or comparison logic.
"""

from collections import Counter
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from feedback.crud import (
    list_all_feedback,
    list_all_hallucination_reports,
    list_all_ratings,
    list_feedback_created_since,
)
from feedback.schemas import AnalyticsResponse

_TREND_WINDOW_DAYS = 30


async def compute_analytics(db: AsyncSession) -> AnalyticsResponse:
    """Compute aggregated analytics across all feedback data.

    Args:
        db: Active async database session.

    Returns:
        AnalyticsResponse: Average rating, positive/negative feedback
            percentages, hallucination report breakdown, most common
            issues, and a 30-day daily submission trend.
    """
    feedback_records = await list_all_feedback(db)
    ratings = await list_all_ratings(db)
    reports = await list_all_hallucination_reports(db)

    thumbs = [record.is_helpful for record in feedback_records if record.is_helpful is not None]
    positive_count = sum(1 for value in thumbs if value is True)
    negative_count = sum(1 for value in thumbs if value is False)
    total_thumbs = positive_count + negative_count

    positive_percent = (positive_count / total_thumbs * 100) if total_thumbs else 0.0
    negative_percent = (negative_count / total_thumbs * 100) if total_thumbs else 0.0

    average_rating = (
        sum(rating.stars for rating in ratings) / len(ratings) if ratings else None
    )

    reason_counts = Counter(report.reason for report in reports)
    most_common_issues = [reason for reason, _count in reason_counts.most_common()]

    since = datetime.now(UTC) - timedelta(days=_TREND_WINDOW_DAYS)
    recent_feedback = await list_feedback_created_since(db, since)
    daily_counts: Counter[str] = Counter()
    for record in recent_feedback:
        day_key = record.created_at.date().isoformat()
        daily_counts[day_key] += 1

    daily_trend = [
        {"date": day, "count": count}
        for day, count in sorted(daily_counts.items())
    ]

    return AnalyticsResponse(
        average_rating=average_rating,
        positive_percent=round(positive_percent, 2),
        negative_percent=round(negative_percent, 2),
        total_feedback=len(feedback_records),
        total_ratings=len(ratings),
        hallucination_reports_by_reason=dict(reason_counts),
        most_common_issues=most_common_issues,
        daily_trend=daily_trend,
    )
