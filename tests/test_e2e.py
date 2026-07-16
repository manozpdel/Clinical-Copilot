"""End-to-end tests exercising the full stack via in-process fakes.

These validate the integration surface between milestones (auth ->
query -> feedback -> health) using the same dependency-override pattern
as the rest of the test suite, so they run without a live Postgres/
Groq/Redis stack. True infra-level e2e verification is the job of
`deployment/scripts/healthcheck.sh` against a running Docker Compose
stack.
"""

import uuid

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

    def run_query(self, question: str, conversation_id: str | None = None) -> dict:
        """Return a canned query result."""
        return {
            "answer": "Patient is taking Metformin 500mg twice daily.",
            "citations": ["[Citation: Patient patient_001, Chunk c1, patient_001.txt]"],
            "evaluation": {"faithfulness": 0.9, "citation_present": True, "context_used": True},
            "latency_seconds": 0.3,
            "conversation_id": conversation_id or uuid.uuid4().hex,
            "request_id": "req-e2e",
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
    """Persist and return a test user."""
    user = User(email="e2e-user@example.com", provider="local")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.mark.e2e
def test_full_query_and_feedback_flow(db_session, test_user) -> None:
    """A user should be able to submit a query, then like it, then see it in history."""
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_query_service] = lambda: _FakeQueryService()

    client = TestClient(app)

    query_response = client.post(
        "/api/query", json={"question": "What medications is patient_001 taking?"}
    )
    assert query_response.status_code == 200
    query_id = query_response.json()["query_id"]

    feedback_response = client.post("/feedback", json={"query_id": query_id, "is_helpful": True})
    assert feedback_response.status_code == 201

    history_response = client.get("/feedback/history")
    assert history_response.status_code == 200
    assert any(item["query_id"] == query_id for item in history_response.json())

    app.dependency_overrides.clear()


@pytest.mark.e2e
def test_health_and_version_endpoints_available_without_auth() -> None:
    """Health/version endpoints should require no authentication."""
    client = TestClient(app)

    assert client.get("/health").status_code == 200
    assert client.get("/api/version").status_code == 200


@pytest.mark.e2e
def test_protected_endpoints_reject_unauthenticated_access() -> None:
    """Query/voice/feedback endpoints should all require authentication."""
    client = TestClient(app)

    assert client.post("/api/query", json={"question": "hi"}).status_code == 401
    assert client.get("/feedback/history").status_code == 401
    assert client.get("/stream/query", params={"question": "hi"}).status_code == 401
