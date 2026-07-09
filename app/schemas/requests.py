"""Request schemas for the Clinical Copilot REST API.

This module is responsible ONLY for validating incoming request
payloads. It contains no routing or business logic.
"""

from pydantic import BaseModel, field_validator


class QueryRequest(BaseModel):
    """Request payload for the text query endpoint.

    Attributes:
        question: The user's natural language question.
        conversation_id: Optional existing conversation identifier to
            continue a prior session.
    """

    question: str
    conversation_id: str | None = None

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        """Reject a blank or whitespace-only question.

        Args:
            value: The raw question string.

        Returns:
            str: The trimmed question string.

        Raises:
            ValueError: If the question is empty or whitespace-only.
        """
        if not value or not value.strip():
            raise ValueError("question must not be empty or blank.")
        return value.strip()