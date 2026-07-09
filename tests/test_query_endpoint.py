"""Tests for the /api/query endpoint."""

from typing import Any

from fastapi.testclient import TestClient

from app.api.query import get_query_service
from app.main import app


class _FakeQueryService:
    """A fake QueryService returning a canned result without network calls."""

    def run_query(
        self, question: str, conversation_id: str | None = None
    ) -> dict[str, Any]:
        """Return a canned query result, ignoring the actual question.

        Args:
            question: The user's natural language question (unused).
            conversation_id: Optional existing conversation identifier.

        Returns:
            dict[str, Any]: A canned result matching QueryResponse.
        """
        return {
            "answer": "Patient is taking Metformin 500mg twice daily.",
            "citations": [
                "[Citation: Patient patient_001, Chunk c1, patient_001.txt]"
            ],
            "evaluation": {
                "faithfulness": 0.9,
                "citation_present": True,
                "context_used": True,
            },
            "latency_seconds": 0.42,
            "conversation_id": conversation_id or "conv-123",
            "request_id": "req-123",
        }


def test_submit_query_returns_answer_and_citations() -> None:
    """A valid question should return an answer, citations, and evaluation."""
    app.dependency_overrides[get_query_service] = lambda: _FakeQueryService()
    client = TestClient(app)

    response = client.post(
        "/api/query", json={"question": "What medications is patient_001 taking?"}
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert "Metformin" in body["answer"]
    assert len(body["citations"]) == 1
    assert body["evaluation"]["faithfulness"] == 0.9
    assert body["latency_seconds"] == 0.42
    assert body["conversation_id"] == "conv-123"


def test_submit_query_rejects_blank_question() -> None:
    """A blank question should fail request validation with a 422.

    The service dependency is overridden with a fake even though this
    test only exercises validation, because FastAPI resolves endpoint
    dependencies as part of handling the request. Without a real API
    key configured (as in CI), constructing the real, agent-backed
    QueryService would raise before validation could reject the
    request.
    """
    app.dependency_overrides[get_query_service] = lambda: _FakeQueryService()
    client = TestClient(app)

    response = client.post("/api/query", json={"question": "   "})

    app.dependency_overrides.clear()

    assert response.status_code == 422


def test_submit_query_preserves_provided_conversation_id() -> None:
    """A provided conversation_id should be passed through to the service."""
    app.dependency_overrides[get_query_service] = lambda: _FakeQueryService()
    client = TestClient(app)

    response = client.post(
        "/api/query",
        json={
            "question": "What allergies does patient_001 have?",
            "conversation_id": "my-convo",
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["conversation_id"] == "my-convo"