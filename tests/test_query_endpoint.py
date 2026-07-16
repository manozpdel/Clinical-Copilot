"""Tests for the /api/query endpoint."""

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.query import get_query_service
from app.core.config import Settings
from app.main import app
from auth.dependencies import get_current_user
from database.base import Base
from database.dependencies import get_db
from database.models import User
from database.session import build_engine, build_session_factory


class _FakeQueryService:
    """A fake QueryService returning a canned result without network calls."""

    def run_query(self, question: str, conversation_id: str | None = None) -> dict[str, Any]:
        """Return a canned query result, ignoring the actual question.

        Args:
            question: The user's natural language question (unused).
            conversation_id: Optional existing conversation identifier.

        Returns:
            dict[str, Any]: A canned result matching QueryResponse.
        """
        return {
            "answer": "Patient is taking Metformin 500mg twice daily.",
            "citations": ["[Citation: Patient patient_001, Chunk c1, patient_001.txt]"],
            "evaluation": {
                "faithfulness": 0.9,
                "citation_present": True,
                "context_used": True,
            },
            "latency_seconds": 0.42,
            "conversation_id": conversation_id or uuid.uuid4().hex,
            "request_id": "req-123",
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
    user = User(email="test-query-user@example.com", provider="local")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def authed_client(db_session, test_user):
    """Provide a TestClient with db and auth dependencies overridden."""
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_query_service] = lambda: _FakeQueryService()

    yield TestClient(app)

    app.dependency_overrides.clear()


def test_submit_query_returns_answer_and_citations(authed_client) -> None:
    """A valid, authenticated question should return an answer and citations."""
    response = authed_client.post(
        "/api/query", json={"question": "What medications is patient_001 taking?"}
    )

    assert response.status_code == 200
    body = response.json()
    assert "Metformin" in body["answer"]
    assert len(body["citations"]) == 1
    assert body["evaluation"]["faithfulness"] == 0.9
    assert body["latency_seconds"] == 0.42


def test_submit_query_rejects_blank_question(authed_client) -> None:
    """A blank question should fail request validation with a 422."""
    response = authed_client.post("/api/query", json={"question": "   "})

    assert response.status_code == 422


def test_submit_query_preserves_provided_conversation_id(authed_client) -> None:
    """A provided conversation_id should be passed through to the service."""
    conversation_id = uuid.uuid4().hex

    response = authed_client.post(
        "/api/query",
        json={
            "question": "What allergies does patient_001 have?",
            "conversation_id": conversation_id,
        },
    )

    assert response.status_code == 200
    assert response.json()["conversation_id"] == conversation_id


def test_submit_query_requires_authentication() -> None:
    """A request without a bearer token should be rejected with a 401."""
    app.dependency_overrides[get_query_service] = lambda: _FakeQueryService()
    client = TestClient(app)

    response = client.post(
        "/api/query", json={"question": "What medications is patient_001 taking?"}
    )

    app.dependency_overrides.clear()

    assert response.status_code == 401
