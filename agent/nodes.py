"""LangGraph node wiring for the Clinical Copilot agent.

This module is responsible ONLY for adapting the pure domain functions
in `planner.py`, `retriever_node.py`, `generator_node.py`, and
`evaluator_node.py` into LangGraph-compatible node callables that
accept and return `AgentState`. It contains no planning, retrieval,
generation, or evaluation logic of its own.
"""

from collections.abc import Callable
from typing import Any

from app.core.config import Settings
from app.core.logging import get_logger
from agent.evaluator_node import evaluate_response
from agent.generator_node import generate_response
from agent.planner import plan
from agent.retriever_node import retrieve_context
from agent.state import AgentState
from ingest.embeddings import EmbeddingModel
from llm.client import GroqClient
from rag.retriever import ChromaRetriever

logger = get_logger(__name__)

NodeFn = Callable[[AgentState], dict[str, Any]]


def make_planner_node() -> NodeFn:
    """Build the LangGraph node function for the planner stage.

    Returns:
        NodeFn: A node function that validates and normalizes the
            question and initializes conversation/request identifiers.
    """

    def node(state: AgentState) -> dict[str, Any]:
        planned_state = plan(
            question=state["question"],
            conversation_id=state.get("conversation_id") or None,
            request_id=state.get("request_id") or None,
        )
        logger.info("planner_node_complete", request_id=planned_state["request_id"])
        return dict(planned_state)

    return node


def make_retriever_node(
    settings: Settings,
    embedder: EmbeddingModel | None = None,
    retriever: ChromaRetriever | None = None,
) -> NodeFn:
    """Build the LangGraph node function for the retriever stage.

    Args:
        settings: Active application settings.
        embedder: Optional embedding model override, for testability.
        retriever: Optional Chroma retriever override, for testability.

    Returns:
        NodeFn: A node function that retrieves and formats context for
            the question.
    """

    def node(state: AgentState) -> dict[str, Any]:
        chunks, context = retrieve_context(
            question=state["question"],
            settings=settings,
            embedder=embedder,
            retriever=retriever,
        )
        metadata = {**state.get("metadata", {}), "stage": "retrieved"}
        logger.info("retriever_node_complete", chunk_count=len(chunks))
        return {
            "retrieved_chunks": chunks,
            "formatted_context": context,
            "metadata": metadata,
        }

    return node


def make_generator_node(client: GroqClient) -> NodeFn:
    """Build the LangGraph node function for the generator stage.

    Args:
        client: GroqClient used for answer generation.

    Returns:
        NodeFn: A node function that generates an answer with
            citations from the retrieved context.
    """

    def node(state: AgentState) -> dict[str, Any]:
        answer, citations, prompt = generate_response(
            question=state["question"],
            chunks=state.get("retrieved_chunks", []),
            client=client,
        )
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
    """Build the LangGraph node function for the evaluator stage.

    Args:
        client: GroqClient used for LLM-as-a-judge faithfulness
            scoring.
        enable_evaluation: Whether faithfulness scoring should run.

    Returns:
        NodeFn: A node function that evaluates the generated answer
            without altering or halting execution based on the score.
    """

    def node(state: AgentState) -> dict[str, Any]:
        evaluation = evaluate_response(
            context=state.get("formatted_context", ""),
            answer=state.get("answer", ""),
            citations=state.get("citations", []),
            client=client,
            enable_evaluation=enable_evaluation,
        )
        metadata = {**state.get("metadata", {}), "stage": "evaluated"}
        logger.info("evaluator_node_complete", evaluation=evaluation)
        return {"evaluation": evaluation, "metadata": metadata}

    return node