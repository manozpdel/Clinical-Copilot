"""Google OAuth ID token verification.

This module is responsible ONLY for verifying a Google-issued ID token
against Google's tokeninfo endpoint and extracting the user's basic
profile. It contains no JWT issuance, password hashing, or CRUD logic.
"""

import httpx
from pydantic import BaseModel

from app.core.config import Settings

_GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"


class GoogleProfile(BaseModel):
    """The subset of a verified Google ID token's claims that we use.

    Attributes:
        email: The verified email address associated with the token.
        name: The user's display name, when provided by Google.
    """

    email: str
    name: str | None = None


class GoogleOAuthError(Exception):
    """Raised when a Google ID token fails verification."""


async def verify_google_id_token(id_token: str, settings: Settings) -> GoogleProfile:
    """Verify a Google-issued ID token and extract the user's profile.

    Args:
        id_token: The raw Google ID token to verify, typically obtained
            client-side via Google Sign-In.
        settings: Active application settings, providing the expected
            OAuth client ID.

    Returns:
        GoogleProfile: The verified user's email and display name.

    Raises:
        GoogleOAuthError: If Google rejects the token, the token was
            not issued for this application, or no email is present.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(_GOOGLE_TOKENINFO_URL, params={"id_token": id_token})

    if response.status_code != 200:
        raise GoogleOAuthError("Google rejected the provided ID token.")

    payload = response.json()

    if payload.get("aud") != settings.google_client_id:
        raise GoogleOAuthError("ID token was not issued for this application.")

    email = payload.get("email")
    if not email:
        raise GoogleOAuthError("Google ID token did not include an email address.")

    return GoogleProfile(email=email, name=payload.get("name"))
