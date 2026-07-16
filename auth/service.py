"""Business logic for registration, login, refresh, and Google login.

This module is responsible ONLY for orchestrating password hashing,
JWT issuance, and user lookups/creation via `database.crud`. It
contains no FastAPI routing, request validation, or raw SQL of its
own.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from auth.jwt import TokenError, create_access_token, create_refresh_token, decode_token
from auth.oauth import GoogleOAuthError, verify_google_id_token
from auth.security import hash_password, verify_password
from database.crud import create_user, get_user_by_email, get_user_by_id
from database.models import User


class AuthError(Exception):
    """Raised when a well-formed authentication request cannot succeed."""


class AuthService:
    """Orchestrates registration, login, token refresh, and Google login."""

    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        """Initialize the auth service.

        Args:
            db: Active async database session.
            settings: Active application settings.
        """
        self._db = db
        self._settings = settings

    def _issue_tokens(self, user: User) -> tuple[str, str]:
        """Issue a fresh access/refresh token pair for a user.

        Args:
            user: The user to issue tokens for.

        Returns:
            tuple[str, str]: The (access_token, refresh_token) pair.
        """
        return (
            create_access_token(user.id, self._settings),
            create_refresh_token(user.id, self._settings),
        )

    async def register(
        self, email: str, password: str, full_name: str | None
    ) -> tuple[User, str, str]:
        """Register a new local user account.

        Args:
            email: The new user's email address.
            password: The new user's plaintext password.
            full_name: Optional display name.

        Returns:
            tuple[User, str, str]: The created user and a fresh
                (access_token, refresh_token) pair.

        Raises:
            AuthError: If a user with this email already exists.
        """
        existing = await get_user_by_email(self._db, email)
        if existing is not None:
            raise AuthError("A user with this email already exists.")

        user = await create_user(
            self._db,
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
            provider="local",
        )
        access_token, refresh_token = self._issue_tokens(user)
        return user, access_token, refresh_token

    async def login(self, email: str, password: str) -> tuple[User, str, str]:
        """Authenticate a local user by email and password.

        Args:
            email: The user's email address.
            password: The user's plaintext password.

        Returns:
            tuple[User, str, str]: The authenticated user and a fresh
                (access_token, refresh_token) pair.

        Raises:
            AuthError: If the email/password combination is invalid,
                or the account has no local password set (e.g. an
                OAuth-only account).
        """
        user = await get_user_by_email(self._db, email)
        if (
            user is None
            or user.hashed_password is None
            or not verify_password(password, user.hashed_password)
        ):
            raise AuthError("Invalid email or password.")

        access_token, refresh_token = self._issue_tokens(user)
        return user, access_token, refresh_token

    async def refresh(self, refresh_token: str) -> tuple[User, str, str]:
        """Exchange a valid refresh token for a new token pair.

        Args:
            refresh_token: The previously issued refresh token.

        Returns:
            tuple[User, str, str]: The user and a fresh
                (access_token, refresh_token) pair.

        Raises:
            AuthError: If the refresh token is invalid, expired, or the
                associated user no longer exists.
        """
        try:
            subject = decode_token(refresh_token, self._settings, expected_type="refresh")
        except TokenError as error:
            raise AuthError("Invalid or expired refresh token.") from error

        user = await get_user_by_id(self._db, subject)
        if user is None:
            raise AuthError("User not found.")

        access_token, new_refresh_token = self._issue_tokens(user)
        return user, access_token, new_refresh_token

    async def google_login(self, id_token: str) -> tuple[User, str, str]:
        """Authenticate (or provision) a user via a Google ID token.

        Args:
            id_token: A Google-issued ID token.

        Returns:
            tuple[User, str, str]: The user (existing or newly created)
                and a fresh (access_token, refresh_token) pair.

        Raises:
            AuthError: If the Google ID token fails verification.
        """
        try:
            profile = await verify_google_id_token(id_token, self._settings)
        except GoogleOAuthError as error:
            raise AuthError(str(error)) from error

        user = await get_user_by_email(self._db, profile.email)
        if user is None:
            user = await create_user(
                self._db,
                email=profile.email,
                hashed_password=None,
                full_name=profile.name,
                provider="google",
            )

        access_token, refresh_token = self._issue_tokens(user)
        return user, access_token, refresh_token
