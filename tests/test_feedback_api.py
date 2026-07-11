"""Tests for the /feedback/* REST endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import app
from auth.dependencies import get_current_user
from database.base import Base
from database.dependencies import get_db
from database.models import Conversation, Query, User
from database.session import build_engine, build_session_factory


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
async def seeded_query(db_session):
    """Seed a user, conversation, and query in the test database."""
    user = User(email="api-fb-user@example.com", provider="local")
    db_session.add(user)
    await db_session.flush()

    conversation = Conversation(user_id=user.id)
    db_session.add(conversation)
    await db_session.flush()

    query = Query(
        conversation_id=conversation.id,
        query_text="What medications is patient_001 taking?",
        response_text="Metformin 500mg twice daily.",
        citations=["[Citation: Patient patient_001, Chunk c1, patient_001.txt]"],
        evaluation={"faithfulness": 0.9},
        latency_ms=100.0,
    )
    db_session.add(query)
    await db_session.commit()
    await db_session.refresh(query)

    return user, query


@pytest.fixture
def client(db_session, seeded_query):
    """Provide a TestClient with db and auth dependencies overridden."""
    user, _ = seeded_query
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: user

    yield TestClient(app)

    app.dependency_overrides.clear()


def test_submit_feedback_endpoint(client, seeded_query) -> None:
    """POST /feedback should create a feedback record."""
    _, query = seeded_query

    response = client.post(
        "/feedback", json={"query_id": str(query.id), "is_helpful": True, "comment": "Nice"}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["is_helpful"] is True
    assert body["comment"] == "Nice"


def test_submit_feedback_unknown_query_returns_404(client) -> None:
    """POST /feedback for a nonexistent query should return 404."""
    import uuid

    response = client.post("/feedback", json={"query_id": str(uuid.uuid4()), "is_helpful": True})

    assert response.status_code == 404


def test_update_feedback_endpoint(client, seeded_query) -> None:
    """PUT /feedback/{id} should update an existing feedback record."""
    _, query = seeded_query

    create_response = client.post("/feedback", json={"query_id": str(query.id), "is_helpful": True})
    feedback_id = create_response.json()["id"]

    update_response = client.put(
        f"/feedback/{feedback_id}", json={"is_helpful": False, "comment": "Changed"}
    )

    assert update_response.status_code == 200
    assert update_response.json()["is_helpful"] is False


def test_delete_feedback_endpoint(client, seeded_query) -> None:
    """DELETE /feedback/{id} should remove the feedback record."""
    _, query = seeded_query

    create_response = client.post("/feedback", json={"query_id": str(query.id), "is_helpful": True})
    feedback_id = create_response.json()["id"]

    delete_response = client.delete(f"/feedback/{feedback_id}")

    assert delete_response.status_code == 204


def test_submit_rating_endpoint(client, seeded_query) -> None:
    """POST /feedback/rating should create a rating record."""
    _, query = seeded_query

    response = client.post("/feedback/rating", json={"query_id": str(query.id), "stars": 5})

    assert response.status_code == 201
    assert response.json()["stars"] == 5


def test_submit_rating_invalid_stars_returns_422(client, seeded_query) -> None:
    """POST /feedback/rating with an out-of-range value should fail validation."""
    _, query = seeded_query

    response = client.post("/feedback/rating", json={"query_id": str(query.id), "stars": 9})

    assert response.status_code == 422


def test_submit_hallucination_report_endpoint(client, seeded_query) -> None:
    """POST /feedback/report should create a hallucination report."""
    _, query = seeded_query

    response = client.post(
        "/feedback/report",
        json={"query_id": str(query.id), "reason": "hallucination", "detail": "Made up a drug"},
    )

    assert response.status_code == 201
    assert response.json()["reason"] == "hallucination"


def test_get_history_endpoint(client, seeded_query) -> None:
    """GET /feedback/history should return the user's own queries."""
    response = client.get("/feedback/history")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["query_text"] == "What medications is patient_001 taking?"


def test_analytics_endpoint_requires_admin(client) -> None:
    """GET /feedback/analytics should be forbidden for non-admin users."""
    response = client.get("/feedback/analytics")

    assert response.status_code == 403


def test_export_endpoint_requires_admin(client) -> None:
    """GET /feedback/export should be forbidden for non-admin users."""
    response = client.get("/feedback/export?format=json")

    assert response.status_code == 403


def test_analytics_endpoint_allowed_for_admin(db_session, seeded_query) -> None:
    """GET /feedback/analytics should succeed for an admin user."""
    user, query = seeded_query
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: user

    admin_client = TestClient(app)

    from app.core.config import get_settings

    def admin_settings():
        settings = get_settings().model_copy(update={"admin_emails": (user.email,)})
        return settings

    from app.core.config import Settings as SettingsClass

    app.dependency_overrides[get_settings] = lambda: SettingsClass(admin_emails=(user.email,))

    response = admin_client.get("/feedback/analytics")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert "average_rating" in body
