"""Tests for session management and isolation."""

from voice.session import SessionManager


def test_create_session_returns_unique_ids() -> None:
    """Creating multiple sessions should return distinct identifiers."""
    manager = SessionManager(max_history=10)

    first_id = manager.create_session()
    second_id = manager.create_session()

    assert first_id != second_id


def test_create_session_accepts_explicit_id() -> None:
    """An explicit session ID should be used as provided."""
    manager = SessionManager(max_history=10)

    session_id = manager.create_session(session_id="my-session")

    assert session_id == "my-session"
    assert "my-session" in manager.list_sessions()


def test_get_memory_creates_session_when_absent() -> None:
    """Requesting memory for an unknown session ID should create it."""
    manager = SessionManager(max_history=10)

    memory = manager.get_memory("new-session")

    assert memory.history() == []
    assert "new-session" in manager.list_sessions()


def test_sessions_are_isolated_from_each_other() -> None:
    """Turns appended to one session's memory should not affect another."""
    manager = SessionManager(max_history=10)

    memory_a = manager.get_memory("session-a")
    memory_b = manager.get_memory("session-b")

    memory_a.append("user", "question in session A")

    assert len(memory_a.history()) == 1
    assert len(memory_b.history()) == 0


def test_reset_session_clears_history_without_deleting_session() -> None:
    """Resetting a session should clear its history but keep it registered."""
    manager = SessionManager(max_history=10)
    memory = manager.get_memory("session-a")
    memory.append("user", "question")

    manager.reset_session("session-a")

    assert manager.get_memory("session-a").history() == []
    assert "session-a" in manager.list_sessions()