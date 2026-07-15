"""Tests for stream event construction and serialization."""

import json

from streaming.events import (
    citation_event,
    error_event,
    evaluation_event,
    finished_event,
    heartbeat_event,
    node_complete_event,
    node_start_event,
    progress_event,
    token_event,
    tool_complete_event,
    tool_start_event,
)
from streaming.serializers import to_json, to_sse


def test_token_event_carries_content_and_index() -> None:
    """A token event should carry both the chunk text and its index."""
    event = token_event("hello", 0)

    assert event.event == "token"
    assert event.data == {"content": "hello", "index": 0}


def test_node_start_and_complete_events() -> None:
    """Node events should carry the node name and, for completion, duration."""
    start = node_start_event("planner")
    complete = node_complete_event("planner", 0.123456)

    assert start.data == {"node": "planner"}
    assert complete.data == {"node": "planner", "duration_seconds": 0.1235}


def test_tool_events() -> None:
    """Tool events should carry the tool name, patient ID, and outcome."""
    start = tool_start_event("ehr", "P0005")
    complete = tool_complete_event("ehr", True, 0.02)

    assert start.data["tool"] == "ehr"
    assert start.data["patient_id"] == "P0005"
    assert complete.data["success"] is True


def test_citation_event() -> None:
    """A citation event should carry all identifying fields."""
    event = citation_event("P0005", "chunk1", "mock_ehr_api", 0.95, "[Citation: ...]")

    assert event.data["patient_id"] == "P0005"
    assert event.data["similarity"] == 0.95


def test_evaluation_event_with_and_without_scores() -> None:
    """An evaluation event should include scores only when provided."""
    progress_only = evaluation_event("Calculating faithfulness...")
    with_scores = evaluation_event("Done", scores={"faithfulness": 0.9})

    assert "scores" not in progress_only.data
    assert with_scores.data["scores"]["faithfulness"] == 0.9


def test_progress_heartbeat_finished_error_events() -> None:
    """The remaining event types should be constructed correctly."""
    progress = progress_event("generator", 75.0)
    heartbeat = heartbeat_event()
    finished = finished_event({"answer": "done"})
    error = error_event("boom")

    assert progress.data == {"stage": "generator", "percent": 75.0}
    assert heartbeat.data == {}
    assert finished.data == {"answer": "done"}
    assert error.data == {"detail": "boom"}


def test_to_sse_produces_valid_sse_format() -> None:
    """to_sse should produce a well-formed 'event:'/'data:' block."""
    event = token_event("hi", 0)

    sse_text = to_sse(event)

    assert sse_text.startswith("event: token\n")
    assert "data: " in sse_text
    assert sse_text.endswith("\n\n")


def test_to_json_produces_parseable_json() -> None:
    """to_json should produce valid JSON containing the event type."""
    event = heartbeat_event()

    json_text = to_json(event)
    parsed = json.loads(json_text)

    assert parsed["event"] == "heartbeat"
