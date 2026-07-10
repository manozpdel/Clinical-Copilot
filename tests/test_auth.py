"""Tests for the AuthService (register, login, refresh)."""

import pytest

from app.core.config import Settings
from auth.service import AuthError, AuthService
from database.base import Base
from database.session import build_engine, build_session_factory


@pytest.fixture
async def auth_service():
    """Provide an AuthService backed by a fresh in-memory SQLite database."""
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:", jwt_secret_key="test-secret-key"
    )
    engine = build_engine(settings)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    factory = build_session_factory(engine)
    async with factory() as db:
        yield AuthService(db, settings)

    await engine.dispose()


async def test_register_creates_user_and_tokens(auth_service) -> None:
    """Registering a new user should return the user and a token pair."""
    user, access_token, refresh_token = await auth_service.register(
        "alice@example.com", "supersecret1", "Alice"
    )

    assert user.email == "alice@example.com"
    assert access_token
    assert refresh_token


async def test_register_rejects_duplicate_email(auth_service) -> None:
    """Registering with an already-used email should raise AuthError."""
    await auth_service.register("bob@example.com", "supersecret1", "Bob")

    with pytest.raises(AuthError):
        await auth_service.register("bob@example.com", "anotherpass1", "Bob Two")


async def test_login_succeeds_with_correct_credentials(auth_service) -> None:
    """Logging in with the correct password should succeed."""
    await auth_service.register("carol@example.com", "supersecret1", "Carol")

    user, access_token, refresh_token = await auth_service.login(
        "carol@example.com", "supersecret1"
    )

    assert user.email == "carol@example.com"
    assert access_token
    assert refresh_token


async def test_login_rejects_wrong_password(auth_service) -> None:
    """Logging in with an incorrect password should raise AuthError."""
    await auth_service.register("dave@example.com", "supersecret1", "Dave")

    with pytest.raises(AuthError):
        await auth_service.login("dave@example.com", "wrongpassword")


async def test_login_rejects_unknown_email(auth_service) -> None:
    """Logging in with an unregistered email should raise AuthError."""
    with pytest.raises(AuthError):
        await auth_service.login("nobody@example.com", "whatever123")


async def test_refresh_issues_new_token_pair(auth_service) -> None:
    """A valid refresh token should yield a new access/refresh token pair."""
    _, _, refresh_token = await auth_service.register(
        "erin@example.com", "supersecret1", "Erin"
    )

    user, new_access_token, new_refresh_token = await auth_service.refresh(
        refresh_token
    )

    assert user.email == "erin@example.com"
    assert new_access_token
    assert new_refresh_token


async def test_refresh_rejects_invalid_token(auth_service) -> None:
    """An invalid refresh token should raise AuthError."""
    with pytest.raises(AuthError):
        await auth_service.refresh("not-a-real-token")
