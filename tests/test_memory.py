"""Tests for reusable conversation memory."""

import pytest

from voice.memory import ConversationMemory


def test_append_and_history_preserve_order() -> None:
    """Appended turns should be returned by history() in insertion order."""
    memory = ConversationMemory(max_history=10)

    memory.append("user", "What medications is patient_001 taking?")
    memory.append("assistant", "Patient is taking Metformin.")

    history = memory.history()

    assert len(history) == 2
    assert history[0].role == "user"
    assert history[1].role == "assistant"


def test_append_rejects_invalid_role() -> None:
    """Appending with an invalid role should raise a ValueError."""
    memory = ConversationMemory(max_history=10)

    with pytest.raises(ValueError):
        memory.append("system", "invalid role")


def test_last_message_returns_most_recent_turn() -> None:
    """last_message() should return the most recently appended turn."""
    memory = ConversationMemory(max_history=10)
    memory.append("user", "first question")
    memory.append("assistant", "first answer")

    last = memory.last_message()

    assert last is not None
    assert last.content == "first answer"


def test_last_message_filters_by_role() -> None:
    """last_message(role=...) should return the most recent turn of that role."""
    memory = ConversationMemory(max_history=10)
    memory.append("user", "first question")
    memory.append("assistant", "first answer")
    memory.append("user", "second question")

    last_user = memory.last_message(role="user")

    assert last_user is not None
    assert last_user.content == "second question"


def test_last_message_returns_none_when_empty() -> None:
    """last_message() on an empty history should return None."""
    memory = ConversationMemory(max_history=10)

    assert memory.last_message() is None


def test_clear_removes_all_turns() -> None:
    """clear() should empty the conversation history."""
    memory = ConversationMemory(max_history=10)
    memory.append("user", "question")

    memory.clear()

    assert memory.history() == []


def test_memory_respects_max_history_limit() -> None:
    """History should be trimmed to max_history, discarding oldest turns first."""
    memory = ConversationMemory(max_history=3)

    for index in range(5):
        memory.append("user", f"question {index}")

    history = memory.history()

    assert len(history) == 3
    assert history[0].content == "question 2"
    assert history[-1].content == "question 4"
