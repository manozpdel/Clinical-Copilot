"""FastAPI dependency injection for authenticated requests.

This module is responsible ONLY for resolving the current user from a
bearer JWT (or, for transports that cannot set custom headers — SSE
via `EventSource` and native WebSockets — a `token` query parameter).
It contains no token encoding, password hashing, or OAuth logic.
"""

from fastapi import Depends, HTTPException, Request, WebSocket, WebSocketException, status
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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")

    try:
        subject = decode_token(credentials.credentials, settings, expected_type="access")
    except TokenError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)) from error

    user = await get_user_by_id(db, subject)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")

    return user


async def get_current_user_query_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve the current user from a bearer header or a `token` query param.

    Used by `GET /stream/query`, since the browser's native
    `EventSource` client cannot set custom request headers, so the
    frontend falls back to passing the access token as `?token=...`.

    Args:
        request: The incoming HTTP request, used to read query params.
        credentials: The parsed `Authorization` header, if present.
        settings: Active application settings.
        db: Request-scoped async database session.

    Returns:
        User: The authenticated user.

    Raises:
        HTTPException: With status 401 if no valid token was found by
            either method.
    """
    token = credentials.credentials if credentials else request.query_params.get("token")

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")

    try:
        subject = decode_token(token, settings, expected_type="access")
    except TokenError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)) from error

    user = await get_user_by_id(db, subject)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")

    return user


async def get_current_user_ws(
    websocket: WebSocket,
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve the current user from a WebSocket's `token` query parameter.

    Native browser WebSockets cannot set an `Authorization` header, so
    the access token is passed as `?token=...` on the connection URL
    instead.

    Args:
        websocket: The incoming WebSocket connection.
        settings: Active application settings.
        db: Request-scoped async database session.

    Returns:
        User: The authenticated user.

    Raises:
        WebSocketException: With code 4401 if no valid token was
            provided or the user could not be resolved.
    """
    token = websocket.query_params.get("token")
    if not token:
        raise WebSocketException(code=4401, reason="Not authenticated.")

    try:
        subject = decode_token(token, settings, expected_type="access")
    except TokenError as error:
        raise WebSocketException(code=4401, reason=str(error)) from error

    user = await get_user_by_id(db, subject)
    if user is None:
        raise WebSocketException(code=4401, reason="User not found.")

    return user
