"""Pydantic models for the voice interaction layer.

This module is responsible ONLY for defining the data shapes used
across the voice package. It contains no audio loading, transcription,
memory, session, or pipeline orchestration logic.
"""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class TranscriptionResult(BaseModel):
    """The result of transcribing an audio file to text.

    Attributes:
        text: The transcribed text.
        language: Detected or configured language code, when available.
        duration_seconds: Duration of the source audio, when reported
            by the transcription provider.
        provider: Name of the transcription provider used, e.g. "groq".
        model: Name of the transcription model used.
    """

    text: str
    language: str | None = None
    duration_seconds: float | None = None
    provider: str
    model: str


class ConversationTurn(BaseModel):
    """A single user/assistant exchange within a conversation session.

    Attributes:
        role: Either "user" or "assistant".
        content: The message text for this turn.
        timestamp: Timezone-aware UTC timestamp when the turn was
            recorded.
    """

    role: str
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class VoiceChatResult(BaseModel):
    """The result of running the full voice pipeline for one audio turn.

    Attributes:
        transcript: The transcribed user question.
        answer: The agent's generated answer, with citations appended.
        citations: Formatted citation strings supporting the answer.
        evaluation: Evaluation metrics computed for the answer.
        conversation_id: Identifier of the conversation session this
            turn belongs to.
        request_id: Identifier unique to this single agent execution.
        history: The full conversation history after this turn was
            recorded, oldest first.
        metadata: Free-form metadata from the underlying agent
            execution.
    """

    transcript: str
    answer: str
    citations: list[str]
    evaluation: dict[str, Any]
    conversation_id: str
    request_id: str
    history: list[ConversationTurn]
    metadata: dict[str, Any]