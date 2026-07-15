"""Tests for the /stream/query SSE endpoint."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import app
from auth.dependencies import get_current_user_query_token
from database.base import Base
from database.dependencies import get_db
from database.models import User
from database.session import build_engine, build_session_factory
from streaming.schemas import StreamEvent
from streaming.sse import get_streaming_service


class _FakeStreamingService:
    """A fake StreamingService yielding a small, fixed event sequence."""

    async def stream_query(self, question, conversation_id, user_id, db):
        """Yield a minimal token/finished sequence."""
        yield StreamEvent(event="node_start", data={"node": "planner"})
        yield StreamEvent(event="token", data={"content": "Hi", "index": 0})
        yield StreamEvent(
            event="finished",
            data={
                "answer": "Hi",
                "citations": [],
                "evaluation": {},
                "latency_seconds": 0.1,
                "conversation_id": "conv-1",
                "request_id": "req-1",
                "query_id": "query-1",
            },
        )


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
    user = User(email="sse-user@example.com", provider="local")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


def test_stream_query_endpoint_returns_event_stream(db_session, test_user) -> None:
    """GET /stream/query should return a text/event-stream response containing events."""
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user_query_token] = lambda: test_user
    app.dependency_overrides[get_streaming_service] = lambda: _FakeStreamingService()

    client = TestClient(app)

    with client.stream("GET", "/stream/query", params={"question": "hi"}) as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        body = "".join(response.iter_text())

    app.dependency_overrides.clear()

    assert "event: node_start" in body
    assert "event: token" in body
    assert "event: finished" in body


def test_stream_query_requires_authentication() -> None:
    """GET /stream/query without a token should return 401."""
    app.dependency_overrides[get_streaming_service] = lambda: _FakeStreamingService()
    client = TestClient(app)

    response = client.get("/stream/query", params={"question": "hi"})

    app.dependency_overrides.clear()

    assert response.status_code == 401
