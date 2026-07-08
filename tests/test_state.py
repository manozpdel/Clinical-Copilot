"""Tests for agent state initialization."""

from agent.state import create_empty_state


def test_create_empty_state_has_all_required_fields() -> None:
    """The empty state should include every field with safe defaults."""
    state = create_empty_state()

    assert state["question"] == ""
    assert state["retrieved_chunks"] == []
    assert state["formatted_context"] == ""
    assert state["prompt"] == ""
    assert state["answer"] == ""
    assert state["citations"] == []
    assert state["evaluation"] == {}
    assert state["metadata"] == {}
    assert state["conversation_id"] == ""
    assert state["request_id"] == ""