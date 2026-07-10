"""Public authentication endpoints.

This module is responsible ONLY for the `/auth/*` and `/login/google`
routes. It contains no business logic; execution is delegated entirely
to `AuthService`. These endpoints are intentionally NOT mounted under
`/api`, matching the public route list for this milestone.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from auth.schemas import (
    GoogleLoginRequest,
    RefreshRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
)
from auth.service import AuthError, AuthService
from database.dependencies import get_db

router = APIRouter(tags=["auth"])


def get_auth_service(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthService:
    """Provide an AuthService bound to the request's database session.

    Args:
        db: Request-scoped async database session.
        settings: Active application settings.

    Returns:
        AuthService: The authentication service instance.
    """
    return AuthService(db, settings)


@router.post("/auth/register", response_model=TokenResponse)
async def register(
    request: UserRegisterRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Register a new local user account and issue tokens.

    Args:
        request: The validated registration request payload.
        service: The auth service, injected via dependency override in
            tests or the default database-backed service in
            production.

    Returns:
        TokenResponse: A fresh access/refresh token pair.

    Raises:
        HTTPException: With status 400 if a user with this email
            already exists.
    """
    try:
        _, access_token, refresh_token = await service.register(
            request.email, request.password, request.full_name
        )
    except AuthError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)
        ) from error

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/auth/login", response_model=TokenResponse)
async def login(
    request: UserLoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Authenticate a local user and issue tokens.

    Args:
        request: The validated login request payload.
        service: The auth service, injected via dependency override in
            tests or the default database-backed service in
            production.

    Returns:
        TokenResponse: A fresh access/refresh token pair.

    Raises:
        HTTPException: With status 401 if the credentials are invalid.
    """
    try:
        _, access_token, refresh_token = await service.login(
            request.email, request.password
        )
    except AuthError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)
        ) from error

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh(
    request: RefreshRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Exchange a valid refresh token for a new token pair.

    Args:
        request: The validated refresh request payload.
        service: The auth service, injected via dependency override in
            tests or the default database-backed service in
            production.

    Returns:
        TokenResponse: A fresh access/refresh token pair.

    Raises:
        HTTPException: With status 401 if the refresh token is invalid
            or expired.
    """
    try:
        _, access_token, refresh_token = await service.refresh(request.refresh_token)
    except AuthError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)
        ) from error

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/login/google", response_model=TokenResponse)
async def login_google(
    request: GoogleLoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Authenticate (or provision) a user via Google OAuth and issue tokens.

    Args:
        request: The validated Google login request payload.
        service: The auth service, injected via dependency override in
            tests or the default database-backed service in
            production.

    Returns:
        TokenResponse: A fresh access/refresh token pair.

    Raises:
        HTTPException: With status 401 if the Google ID token fails
            verification.
    """
    try:
        _, access_token, refresh_token = await service.google_login(request.id_token)
    except AuthError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)
        ) from error

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)
