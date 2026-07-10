"""Response schemas for the Clinical Copilot REST API.

This module is responsible ONLY for defining outgoing response
payloads. It contains no routing or business logic.
"""

from pydantic import BaseModel


class EvaluationScores(BaseModel):
    """Evaluation metrics attached to a generated answer.

    Attributes:
        faithfulness: Faithfulness score in [0.0, 1.0], or None when
            evaluation was skipped.
        citation_present: Whether at least one citation was produced.
        context_used: Whether retrieved/tool context was actually used.
    """

    faithfulness: float | None = None
    citation_present: bool | None = None
    context_used: bool | None = None


class QueryResponse(BaseModel):
    """Response payload for the text query endpoint.

    Attributes:
        answer: The generated answer, with citations appended.
        citations: Formatted citation strings supporting the answer.
        evaluation: Evaluation metrics computed for the answer.
        latency_seconds: Wall-clock time taken to produce the answer.
        conversation_id: Identifier of the conversation session.
        request_id: Identifier unique to this request.
    """

    answer: str
    citations: list[str]
    evaluation: EvaluationScores
    latency_seconds: float
    conversation_id: str
    request_id: str


class VoiceResponse(BaseModel):
    """Response payload for the voice query endpoint.

    Attributes:
        transcript: The transcribed user question.
        answer: The generated answer, with citations appended.
        citations: Formatted citation strings supporting the answer.
        evaluation: Evaluation metrics computed for the answer.
        conversation_id: Identifier of the conversation session.
        request_id: Identifier unique to this request.
    """

    transcript: str
    answer: str
    citations: list[str]
    evaluation: EvaluationScores
    conversation_id: str
    request_id: str


class HealthResponse(BaseModel):
    """Response payload for the API health endpoint.

    Attributes:
        status: The current health status, e.g. "healthy".
    """

    status: str


class VersionResponse(BaseModel):
    """Response payload for the API version endpoint.

    Attributes:
        version: The current API version identifier.
        environment: The active deployment environment.
        status: The current application status, e.g. "operational".
    """

    version: str
    environment: str
    status: str
