"""Session management for the voice interaction layer.

This module is responsible ONLY for creating, looking up, and
resetting conversation sessions, each backed by its own isolated
`ConversationMemory` instance. It contains no transcription, memory
storage internals, or pipeline orchestration logic beyond session
bookkeeping.
"""

import uuid

from voice.memory import ConversationMemory


class SessionManager:
    """Manages isolated conversation sessions, each with its own memory."""

    def __init__(self, max_history: int = 20) -> None:
        """Initialize an empty session manager.

        Args:
            max_history: Maximum number of turns retained per session's
                conversation memory.
        """
        self._max_history = max_history
        self._sessions: dict[str, ConversationMemory] = {}

    def create_session(self, session_id: str | None = None) -> str:
        """Create a new, empty conversation session.

        Args:
            session_id: Optional explicit session identifier. A new
                UUID4 hex string is generated when not provided.

        Returns:
            str: The identifier of the newly created session.
        """
        resolved_id = session_id or uuid.uuid4().hex
        self._sessions[resolved_id] = ConversationMemory(max_history=self._max_history)
        return resolved_id

    def get_memory(self, session_id: str) -> ConversationMemory:
        """Retrieve the conversation memory for a session, creating it if absent.

        Args:
            session_id: The session identifier to look up.

        Returns:
            ConversationMemory: The session's conversation memory. A new
                session is transparently created if `session_id` was
                not previously known.
        """
        if session_id not in self._sessions:
            self._sessions[session_id] = ConversationMemory(
                max_history=self._max_history
            )
        return self._sessions[session_id]

    def reset_session(self, session_id: str) -> None:
        """Clear a session's conversation history without deleting the session.

        Args:
            session_id: The session identifier to reset.
        """
        self.get_memory(session_id).clear()

    def list_sessions(self) -> list[str]:
        """List the identifiers of all known sessions.

        Returns:
            list[str]: Session identifiers, in creation order.
        """
        return list(self._sessions.keys())
