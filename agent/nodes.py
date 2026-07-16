"""LangGraph node wiring for the Clinical Copilot agent.

This module is responsible ONLY for adapting the pure domain functions
in `planner.py`, `retriever_node.py`, `generator_node.py`,
`evaluator_node.py`, and the `tools` package into LangGraph-compatible
node callables that accept and return `AgentState`. It contains no
planning, retrieval, generation, evaluation, or tool-execution logic
of its own. Each node is timed and traced via `observability`, without
altering any node's business logic. `tool_output_to_chunk` is public
so `streaming.service.StreamingService` can reuse the same
tool-output-to-chunk adaptation without duplicating it.
"""

import time
from collections.abc import Callable
from typing import Any

from agent.evaluator_node import evaluate_response
from agent.generator_node import generate_response
from agent.planner import plan
from agent.retriever_node import retrieve_context
from agent.state import AgentState
from app.core.config import Settings
from app.core.logging import get_logger
from ingest.embeddings import EmbeddingModel
from llm.client import GroqClient
from llm.prompts import build_context
from observability.metrics import record_node_duration
from observability.tracing import trace_span
from rag.models import RetrievedChunk
from rag.retriever import ChromaRetriever
from tools.models import ToolName
from tools.router import ToolRouter

logger = get_logger(__name__)

NodeFn = Callable[[AgentState], dict[str, Any]]


def make_planner_node() -> NodeFn:
    """Build the LangGraph node function for the planner stage."""

    def node(state: AgentState) -> dict[str, Any]:
        start = time.monotonic()
        with trace_span("agent.planner"):
            planned_state = plan(
                question=state["question"],
                conversation_id=state.get("conversation_id") or None,
                request_id=state.get("request_id") or None,
            )
        record_node_duration("planner", time.monotonic() - start)
        logger.info("planner_node_complete", request_id=planned_state["request_id"])
        return dict(planned_state)

    return node


def tool_output_to_chunk(tool_name: str, patient_id: str, data: dict[str, Any]) -> RetrievedChunk:
    """Adapt a mock tool's structured output into a RetrievedChunk.

    This lets the existing generator/evaluator nodes and the streaming
    service (which all operate on `RetrievedChunk` objects) consume
    tool output without any modification, avoiding duplicated
    generation, citation, or event-building logic.

    Args:
        tool_name: Name of the mock tool that produced the data.
        patient_id: Identifier of the patient the data belongs to.
        data: The tool's structured output payload.

    Returns:
        RetrievedChunk: A synthetic chunk wrapping the tool output.
    """
    lines = [f"{key.replace('_', ' ').title()}: {value}" for key, value in data.items()]
    text = "\n".join(lines)

    return RetrievedChunk(
        chunk_id=f"tool_{tool_name}_{patient_id}",
        patient_id=patient_id,
        source_file=f"mock_{tool_name}_api",
        text=text,
        similarity=1.0,
    )


def make_tool_router_node(tool_router: ToolRouter) -> NodeFn:
    """Build the LangGraph node function for the tool routing stage."""

    def node(state: AgentState) -> dict[str, Any]:
        start = time.monotonic()
        with trace_span("agent.tool_router"):
            result = tool_router.route(state["question"])
        record_node_duration("tool_router", time.monotonic() - start)

        metadata = {
            **state.get("metadata", {}),
            "stage": "routed",
            "selected_tool": result.tool_name,
        }

        if result.tool_name == ToolName.RETRIEVAL.value or result.output is None:
            logger.info("tool_router_node_complete", selected_tool=result.tool_name)
            return {
                "selected_tool": result.tool_name,
                "tool_output": None,
                "metadata": metadata,
            }

        chunk = tool_output_to_chunk(
            tool_name=result.tool_name,
            patient_id=result.patient_id or "unknown",
            data=result.output.data,
        )
        context = build_context([chunk])

        logger.info(
            "tool_router_node_complete",
            selected_tool=result.tool_name,
            patient_id=result.patient_id,
        )
        return {
            "selected_tool": result.tool_name,
            "tool_output": result.output.data,
            "retrieved_chunks": [chunk],
            "formatted_context": context,
            "metadata": metadata,
        }

    return node


def make_retriever_node(
    settings: Settings,
    embedder: EmbeddingModel | None = None,
    retriever: ChromaRetriever | None = None,
) -> NodeFn:
    """Build the LangGraph node function for the retriever stage."""

    def node(state: AgentState) -> dict[str, Any]:
        start = time.monotonic()
        with trace_span("agent.retriever"):
            chunks, context = retrieve_context(
                question=state["question"],
                settings=settings,
                embedder=embedder,
                retriever=retriever,
            )
        record_node_duration("retriever", time.monotonic() - start)

        metadata = {**state.get("metadata", {}), "stage": "retrieved"}
        logger.info("retriever_node_complete", chunk_count=len(chunks))
        return {
            "retrieved_chunks": chunks,
            "formatted_context": context,
            "metadata": metadata,
        }

    return node


def make_generator_node(client: GroqClient) -> NodeFn:
    """Build the LangGraph node function for the generator stage."""

    def node(state: AgentState) -> dict[str, Any]:
        start = time.monotonic()
        with trace_span("agent.generator"):
            answer, citations, prompt = generate_response(
                question=state["question"],
                chunks=state.get("retrieved_chunks", []),
                client=client,
            )
        record_node_duration("generator", time.monotonic() - start)

        metadata = {**state.get("metadata", {}), "stage": "generated"}
        logger.info("generator_node_complete", citation_count=len(citations))
        return {
            "answer": answer,
            "citations": citations,
            "prompt": prompt.user_prompt,
            "metadata": metadata,
        }

    return node


def make_evaluator_node(client: GroqClient, enable_evaluation: bool) -> NodeFn:
    """Build the LangGraph node function for the evaluator stage."""

    def node(state: AgentState) -> dict[str, Any]:
        start = time.monotonic()
        with trace_span("agent.evaluator"):
            evaluation = evaluate_response(
                context=state.get("formatted_context", ""),
                answer=state.get("answer", ""),
                citations=state.get("citations", []),
                client=client,
                enable_evaluation=enable_evaluation,
            )
        record_node_duration("evaluator", time.monotonic() - start)

        metadata = {**state.get("metadata", {}), "stage": "evaluated"}
        logger.info("evaluator_node_complete", evaluation=evaluation)
        return {"evaluation": evaluation, "metadata": metadata}

    return node
