"""FastAPI dependency injection for the human feedback system.

This module is responsible ONLY for constructing request-scoped
`FeedbackService` instances and enforcing admin-only access to
analytics/export endpoints. It contains no business logic of its own.
"""

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from auth.dependencies import get_current_user
from database.dependencies import get_db
from database.models import User
from feedback.service import FeedbackService


def get_feedback_service(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> FeedbackService:
    """Provide a FeedbackService bound to the request's database session.

    Args:
        db: Request-scoped async database session.
        settings: Active application settings.

    Returns:
        FeedbackService: The feedback service instance.
    """
    return FeedbackService(db, settings)


async def require_admin(
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> User:
    """Restrict access to users whose email is in the configured admin list.

    Args:
        current_user: The authenticated user, resolved from the bearer
            JWT.
        settings: Active application settings, providing `admin_emails`.

    Returns:
        User: The authenticated admin user.

    Raises:
        HTTPException: With status 403 if the user's email is not in
            `settings.admin_emails`.
    """
    if current_user.email not in settings.admin_emails:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires administrator access.",
        )
    return current_user
