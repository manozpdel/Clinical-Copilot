"""Planning logic for the Clinical Copilot agent.

This module is responsible ONLY for validating and normalizing the
incoming question and preparing the initial agent state. It performs
no LLM reasoning, retrieval, or generation.
"""

from agent.state import AgentState, create_empty_state
from agent.utils import generate_id, normalize_whitespace


def plan(
    question: str,
    conversation_id: str | None = None,
    request_id: str | None = None,
) -> AgentState:
    """Validate the question and build the initial agent state.

    Args:
        question: The raw user question.
        conversation_id: Optional existing conversation identifier. A
            new identifier is generated when not provided.
        request_id: Optional existing request identifier. A new
            identifier is generated when not provided.

    Returns:
        AgentState: The initial state, with a normalized question and
            resolved conversation/request identifiers.

    Raises:
        ValueError: If the question is empty or contains only
            whitespace.
    """
    if not question or not question.strip():
        raise ValueError("question must not be empty.")

    state = create_empty_state()
    state["question"] = normalize_whitespace(question)
    state["conversation_id"] = conversation_id or generate_id()
    state["request_id"] = request_id or generate_id()
    state["metadata"] = {"stage": "planned"}

    return state