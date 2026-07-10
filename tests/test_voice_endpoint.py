"""Tests for the /api/voice endpoint."""

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.voice import get_voice_service
from app.core.config import Settings
from app.main import app
from auth.dependencies import get_current_user
from database.base import Base
from database.dependencies import get_db
from database.models import User
from database.session import build_engine, build_session_factory


class _FakeVoiceService:
    """A fake VoiceService returning a canned result without network calls."""

    def run_voice(
        self,
        audio_bytes: bytes,
        filename: str,
        conversation_id: str | None = None,
    ) -> dict[str, Any]:
        """Return a canned voice result, ignoring the actual audio content.

        Args:
            audio_bytes: The raw uploaded audio file contents (unused).
            filename: The original uploaded filename (unused).
            conversation_id: Optional existing conversation identifier.

        Returns:
            dict[str, Any]: A canned result matching VoiceResponse.
        """
        return {
            "transcript": "What medications is patient_001 taking?",
            "answer": "Patient is taking Metformin 500mg twice daily.",
            "citations": ["[Citation: Patient patient_001, Chunk c1, patient_001.txt]"],
            "evaluation": {
                "faithfulness": 0.85,
                "citation_present": True,
                "context_used": True,
            },
            "conversation_id": conversation_id or uuid.uuid4().hex,
            "request_id": "req-456",
        }


@pytest.fixture
async def db_session():
    """Provide a fresh in-memory SQLite session with tables created."""
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:")
    engine = build_engine(settings)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    factory = build_session_factory(engine)
    async with factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def test_user(db_session):
    """Persist and return a test user in the sqlite database."""
    user = User(email="test-voice-user@example.com", provider="local")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def authed_client(db_session, test_user):
    """Provide a TestClient with db and auth dependencies overridden."""
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_voice_service] = lambda: _FakeVoiceService()

    yield TestClient(app)

    app.dependency_overrides.clear()


def test_submit_voice_returns_transcript_and_answer(authed_client) -> None:
    """A valid, authenticated audio upload should return a transcript and answer."""
    response = authed_client.post(
        "/api/voice",
        files={"file": ("clip.wav", b"RIFF" + b"\x00" * 40, "audio/wav")},
    )

    assert response.status_code == 200
    body = response.json()
    assert "medications" in body["transcript"]
    assert "Metformin" in body["answer"]
    assert len(body["citations"]) == 1
    assert body["evaluation"]["faithfulness"] == 0.85


def test_submit_voice_rejects_oversized_upload(authed_client) -> None:
    """An upload exceeding max_upload_size should return a 413 error."""
    oversized_content = b"\x00" * 11_000_000

    response = authed_client.post(
        "/api/voice",
        files={"file": ("clip.wav", oversized_content, "audio/wav")},
    )

    assert response.status_code == 413


def test_submit_voice_preserves_provided_conversation_id(authed_client) -> None:
    """A provided conversation_id form field should be passed to the service."""
    conversation_id = uuid.uuid4().hex

    response = authed_client.post(
        "/api/voice",
        files={"file": ("clip.wav", b"RIFF" + b"\x00" * 40, "audio/wav")},
        data={"conversation_id": conversation_id},
    )

    assert response.status_code == 200
    assert response.json()["conversation_id"] == conversation_id


def test_submit_voice_requires_authentication() -> None:
    """A request without a bearer token should be rejected with a 401."""
    app.dependency_overrides[get_voice_service] = lambda: _FakeVoiceService()
    client = TestClient(app)

    response = client.post(
        "/api/voice",
        files={"file": ("clip.wav", b"RIFF" + b"\x00" * 40, "audio/wav")},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 401
