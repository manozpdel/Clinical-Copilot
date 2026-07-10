"""FastAPI dependency injection for authenticated requests.

This module is responsible ONLY for resolving the current user from a
bearer JWT. It contains no token encoding, password hashing, or OAuth
logic.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from auth.jwt import TokenError, decode_token
from database.crud import get_user_by_id
from database.dependencies import get_db
from database.models import User

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve the authenticated user from the request's bearer token.

    Args:
        credentials: The parsed `Authorization: Bearer <token>` header,
            or None if absent.
        settings: Active application settings.
        db: Request-scoped async database session.

    Returns:
        User: The authenticated user.

    Raises:
        HTTPException: With status 401 if no token was provided, the
            token is invalid or expired, or the user no longer exists.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated."
        )

    try:
        subject = decode_token(
            credentials.credentials, settings, expected_type="access"
        )
    except TokenError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)
        ) from error

    user = await get_user_by_id(db, subject)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found."
        )

    return user
