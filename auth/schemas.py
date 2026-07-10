"""Request/response schemas for authentication endpoints.

This module is responsible ONLY for validating authentication payloads
and shaping authentication responses. It contains no routing, hashing,
JWT, or OAuth logic.
"""
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserRegisterRequest(BaseModel):
    """Request payload for registering a new local user.

    Attributes:
        email: The new user's email address.
        password: The new user's plaintext password.
        full_name: Optional display name.
    """

    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str | None = None


class UserLoginRequest(BaseModel):
    """Request payload for logging in with email and password.

    Attributes:
        email: The user's email address.
        password: The user's plaintext password.
    """

    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    """Request payload for exchanging a refresh token for new tokens.

    Attributes:
        refresh_token: The previously issued refresh token.
    """

    refresh_token: str


class GoogleLoginRequest(BaseModel):
    """Request payload for logging in via Google OAuth.

    Attributes:
        id_token: A Google-issued ID token, typically obtained
            client-side via Google Sign-In.
    """

    id_token: str


class UserResponse(BaseModel):
    """A user's public profile information.

    Attributes:
        id: The user's unique identifier.
        email: The user's email address.
        full_name: The user's display name, when known.
        provider: Authentication provider, e.g. "local" or "google".
    """

    id: str
    email: str
    full_name: str | None
    provider: str


class UserProfileResponse(BaseModel):
    """Extended profile information for the authenticated user.

    Attributes:
        id: The user's unique identifier.
        email: The user's email address.
        full_name: The user's display name, when known.
        provider: Authentication provider, e.g. "local" or "google".
        created_at: Timestamp the account was created.
    """

    id: str
    email: str
    full_name: str | None
    provider: str
    created_at: datetime


class TokenResponse(BaseModel):
    """A pair of issued JWTs.

    Attributes:
        access_token: The short-lived access token.
        refresh_token: The longer-lived refresh token.
        token_type: The token scheme, always "bearer".
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
