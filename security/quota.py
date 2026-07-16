"""Per-user quota enforcement.

This module is responsible ONLY for checking a user's quota status
before allowing a request through. It contains no token/cost
calculation (see `security.budget`) or raw persistence logic beyond
calling `database.crud`.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from database.crud import get_or_create_quota, reset_quota_periods
from security.models import Quota


class QuotaExceededError(Exception):
    """Raised when a user has exceeded one of their configured quotas."""


async def get_current_quota(db: AsyncSession, user_id: UUID) -> Quota:
    """Fetch a user's quota, resetting expired daily/monthly periods first.

    Args:
        db: Active async database session.
        user_id: Identifier of the user.

    Returns:
        Quota: The user's current, up-to-date quota record.
    """
    quota = await get_or_create_quota(db, user_id)
    return await reset_quota_periods(db, quota)


async def check_quota_before_request(db: AsyncSession, user_id: UUID, settings: Settings) -> Quota:
    """Verify a user has remaining quota before an agent call is made.

    Checks the daily request count, monthly token count, and monthly
    cost against the configured limits. Since actual token/cost for the
    upcoming call is not yet known, this is a pre-check against
    already-accumulated usage; the call's own usage is recorded
    separately after it completes via `database.crud.create_usage_log`
    and `database.crud.increment_quota_usage`.

    Args:
        db: Active async database session.
        user_id: Identifier of the requesting user.
        settings: Active application settings, providing the configured
            limits.

    Returns:
        Quota: The user's current quota record.

    Raises:
        QuotaExceededError: If any configured limit has already been
            reached.
    """
    quota = await get_current_quota(db, user_id)

    if quota.daily_request_count >= settings.daily_request_limit:
        raise QuotaExceededError(
            f"Daily request limit of {settings.daily_request_limit} reached. "
            "Please try again tomorrow."
        )

    if quota.monthly_token_count >= settings.monthly_token_limit:
        raise QuotaExceededError(
            f"Monthly token limit of {settings.monthly_token_limit} reached. "
            "Please try again next month."
        )

    if quota.monthly_cost_usd >= settings.monthly_cost_limit:
        raise QuotaExceededError(
            f"Monthly cost limit of ${settings.monthly_cost_limit:.2f} reached. "
            "Please try again next month."
        )

    return quota
