"""Agent state definitions for the Clinical Copilot LangGraph agent.

This module is responsible ONLY for defining the shape of state that
flows through the graph. It contains no node logic, retrieval logic,
or generation logic.
"""

from typing import Any, TypedDict

from rag.models import RetrievedChunk


class AgentState(TypedDict, total=False):
    """State passed between nodes in the Clinical Copilot agent graph.

    Attributes:
        question: The normalized user question.
        retrieved_chunks: Chunks retrieved for the question.
        formatted_context: The retrieved chunks assembled into a single
            context block.
        prompt: The user-facing prompt sent to the language model.
        answer: The generated answer, with citations appended.
        citations: Formatted citation strings supporting the answer.
        evaluation: Evaluation metrics computed for the answer.
        metadata: Free-form metadata tracking pipeline progress and
            timing.
        conversation_id: Identifier grouping related turns together.
        request_id: Identifier unique to this single graph execution.
    """

    question: str
    retrieved_chunks: list[RetrievedChunk]
    formatted_context: str
    prompt: str
    answer: str
    citations: list[str]
    evaluation: dict[str, Any]
    metadata: dict[str, Any]
    conversation_id: str
    request_id: str


def create_empty_state() -> AgentState:
    """Build an empty, fully-initialized AgentState.

    Returns:
        AgentState: A state dict with every field present at a safe
            default value, suitable as the initial input to the graph.
    """
    return AgentState(
        question="",
        retrieved_chunks=[],
        formatted_context="",
        prompt="",
        answer="",
        citations=[],
        evaluation={},
        metadata={},
        conversation_id="",
        request_id="",
    )