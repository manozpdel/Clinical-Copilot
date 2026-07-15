"""Tests for the /ws WebSocket endpoint."""

import pytest

from app.core.config import Settings
from app.main import app
from auth.dependencies import get_current_user_ws
from database.base import Base
from database.dependencies import get_db
from database.models import User
from database.session import build_engine, build_session_factory
from streaming.schemas import StreamEvent
from streaming.websocket import get_streaming_service


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
    user = User(email="ws-user@example.com", provider="local")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


def test_websocket_streams_events(db_session, test_user) -> None:
    """Connecting to /ws and sending a question should stream back events."""
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user_ws] = lambda: test_user
    app.dependency_overrides[get_streaming_service] = lambda: _FakeStreamingService()

    client = __import__("fastapi.testclient", fromlist=["TestClient"]).TestClient(app)

    with client.websocket_connect("/ws?token=fake") as websocket:
        websocket.send_json({"question": "hi"})

        received = []
        for _ in range(3):
            received.append(websocket.receive_json())

    app.dependency_overrides.clear()

    event_types = [item["event"] for item in received]
    assert event_types == ["node_start", "token", "finished"]


def test_websocket_rejects_empty_question(db_session, test_user) -> None:
    """Sending an empty question should return an error event without crashing."""
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user_ws] = lambda: test_user
    app.dependency_overrides[get_streaming_service] = lambda: _FakeStreamingService()

    from fastapi.testclient import TestClient

    client = TestClient(app)

    with client.websocket_connect("/ws?token=fake") as websocket:
        websocket.send_json({"question": "   "})
        response = websocket.receive_json()

    app.dependency_overrides.clear()

    assert response["event"] == "error"
