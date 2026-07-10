"""JWT access and refresh token creation and verification.

This module is responsible ONLY for encoding and decoding JWTs. It
contains no password hashing, OAuth, or dependency-injection logic.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from jose import JWTError, jwt

from app.core.config import Settings


class TokenError(Exception):
    """Raised when a JWT is invalid, expired, malformed, or of the
    wrong type."""


def _create_token(
    subject: str, expires_delta: timedelta, token_type: str, settings: Settings
) -> str:
    """Encode a signed JWT for the given subject and type.

    Args:
        subject: The token subject (typically a user ID string).
        expires_delta: How long the token remains valid.
        token_type: Either "access" or "refresh".
        settings: Active application settings, providing the signing
            key and algorithm.

    Returns:
        str: The encoded JWT.
    """
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


def create_access_token(user_id: UUID, settings: Settings) -> str:
    """Create a signed access token for a user.

    Args:
        user_id: The user's unique identifier.
        settings: Active application settings.

    Returns:
        str: The encoded access token.
    """
    return _create_token(
        str(user_id),
        timedelta(minutes=settings.access_token_expire_minutes),
        "access",
        settings,
    )


def create_refresh_token(user_id: UUID, settings: Settings) -> str:
    """Create a signed refresh token for a user.

    Args:
        user_id: The user's unique identifier.
        settings: Active application settings.

    Returns:
        str: The encoded refresh token.
    """
    return _create_token(
        str(user_id),
        timedelta(days=settings.refresh_token_expire_days),
        "refresh",
        settings,
    )


def decode_token(token: str, settings: Settings, expected_type: str) -> str:
    """Decode and validate a JWT, returning its subject.

    Args:
        token: The encoded JWT to decode.
        settings: Active application settings, providing the signing
            key and algorithm.
        expected_type: The required "type" claim value, either
            "access" or "refresh".

    Returns:
        str: The token's subject (the user ID string).

    Raises:
        TokenError: If the token is invalid, expired, malformed, of the
            wrong type, or missing a subject.
    """
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
    except JWTError as error:
        raise TokenError("Invalid or expired token.") from error

    if payload.get("type") != expected_type:
        raise TokenError(f"Expected a '{expected_type}' token.")

    subject = payload.get("sub")
    if not subject:
        raise TokenError("Token is missing a subject.")

    return subject
