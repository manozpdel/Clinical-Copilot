"""Reusable conversation memory for the voice interaction layer.

This module is responsible ONLY for storing and retrieving
conversation turns. It has no dependency on LangGraph, FastAPI, or any
other orchestration layer, so it can be reused directly by a future
FastAPI service or any other interface.
"""

from voice.models import ConversationTurn


class ConversationMemory:
    """In-memory store of user/assistant turns for a single conversation."""

    def __init__(self, max_history: int = 20) -> None:
        """Initialize empty conversation memory.

        Args:
            max_history: Maximum number of turns retained. Once
                exceeded, the oldest turns are discarded first.
        """
        self._max_history = max_history
        self._turns: list[ConversationTurn] = []

    def append(self, role: str, content: str) -> ConversationTurn:
        """Append a new turn to the conversation history.

        Args:
            role: Either "user" or "assistant".
            content: The message text for this turn.

        Returns:
            ConversationTurn: The newly appended turn.

        Raises:
            ValueError: If `role` is not "user" or "assistant".
        """
        if role not in ("user", "assistant"):
            raise ValueError("role must be either 'user' or 'assistant'.")

        turn = ConversationTurn(role=role, content=content)
        self._turns.append(turn)

        if len(self._turns) > self._max_history:
            self._turns = self._turns[-self._max_history :]

        return turn

    def clear(self) -> None:
        """Remove all turns from the conversation history."""
        self._turns = []

    def history(self) -> list[ConversationTurn]:
        """Return the full stored conversation history.

        Returns:
            list[ConversationTurn]: All retained turns, oldest first.
        """
        return list(self._turns)

    def last_message(self, role: str | None = None) -> ConversationTurn | None:
        """Return the most recent turn, optionally filtered by role.

        Args:
            role: When provided, only consider turns with this role.

        Returns:
            ConversationTurn | None: The most recent matching turn, or
                None if no turns are stored (or none match `role`).
        """
        candidates = (
            self._turns
            if role is None
            else [turn for turn in self._turns if turn.role == role]
        )
        return candidates[-1] if candidates else None
