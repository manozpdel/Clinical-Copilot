"""Agent state definitions for the Clinical Copilot LangGraph agent.

This module is responsible ONLY for defining the shape of state that
flows through the graph. It contains no node logic, retrieval logic,
generation logic, or tool logic.
"""

from typing import Any, TypedDict

from rag.models import RetrievedChunk


class AgentState(TypedDict, total=False):
    """State passed between nodes in the Clinical Copilot agent graph.

    Attributes:
        question: The normalized user question.
        selected_tool: Name of the tool selected by the tool router, or
            "retrieval" when no mock tool applies.
        tool_output: Raw structured data returned by the selected mock
            tool, or None when retrieval was selected instead.
        retrieved_chunks: Chunks retrieved for the question, either from
            semantic retrieval or adapted from a mock tool's output.
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
    selected_tool: str
    tool_output: dict[str, Any] | None
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
        selected_tool="",
        tool_output=None,
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