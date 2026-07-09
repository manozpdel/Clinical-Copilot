"""Business logic for the text query REST endpoint.

This module is responsible ONLY for orchestrating a single question
through the existing LangGraph agent graph (Parts 5/6) and shaping the
result for the API layer. It contains no FastAPI routing, request
validation, or graph-construction logic of its own.
"""

import time
import uuid
from typing import Any

from langgraph.graph.state import CompiledStateGraph

from agent.state import create_empty_state
from app.core.logging import get_logger

logger = get_logger(__name__)


class QueryService:
    """Runs a text question through the existing agent graph."""

    def __init__(self, graph: CompiledStateGraph) -> None:
        """Initialize the query service.

        Args:
            graph: The compiled LangGraph agent graph, reused unchanged
                from Parts 5/6.
        """
        self._graph = graph

    def run_query(
        self, question: str, conversation_id: str | None = None
    ) -> dict[str, Any]:
        """Run a question through the agent graph and time the execution.

        Args:
            question: The user's natural language question.
            conversation_id: Optional existing conversation identifier.
                A new identifier is generated when not provided.

        Returns:
            dict[str, Any]: A mapping with `answer`, `citations`,
                `evaluation`, `latency_seconds`, `conversation_id`, and
                `request_id`, ready to construct a `QueryResponse`.
        """
        start_time = time.monotonic()

        initial_state = create_empty_state()
        initial_state["question"] = question
        initial_state["conversation_id"] = conversation_id or uuid.uuid4().hex
        initial_state["request_id"] = uuid.uuid4().hex

        final_state: dict[str, Any] = dict(initial_state)
        for step in self._graph.stream(initial_state):
            for _node_name, node_update in step.items():
                final_state.update(node_update)

        latency = time.monotonic() - start_time
        logger.info(
            "query_service_completed",
            request_id=final_state.get("request_id"),
            latency_seconds=latency,
        )

        return {
            "answer": final_state.get("answer", ""),
            "citations": final_state.get("citations", []),
            "evaluation": final_state.get("evaluation", {}),
            "latency_seconds": latency,
            "conversation_id": final_state.get("conversation_id", ""),
            "request_id": final_state.get("request_id", ""),
        }