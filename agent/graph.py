"""LangGraph graph construction for the Clinical Copilot agent.

This module is responsible ONLY for wiring node functions into a
compiled LangGraph graph. It contains no planning, retrieval,
generation, or evaluation logic; those live in their respective
modules and are only orchestrated here. The graph is deliberately
linear (Planner -> Retriever -> Generator -> Evaluator -> END) so that
future milestones can extend it with tool nodes, conditional edges,
and memory without restructuring this module.
"""

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.core.config import Settings, get_settings
from agent.nodes import (
    make_evaluator_node,
    make_generator_node,
    make_planner_node,
    make_retriever_node,
)
from agent.state import AgentState
from ingest.embeddings import EmbeddingModel
from llm.client import GroqClient, build_faithfulness_client, build_generation_client
from rag.retriever import ChromaRetriever


def build_graph(
    settings: Settings | None = None,
    generation_client: GroqClient | None = None,
    evaluation_client: GroqClient | None = None,
    embedder: EmbeddingModel | None = None,
    retriever: ChromaRetriever | None = None,
) -> CompiledStateGraph:
    """Build and compile the Clinical Copilot agent graph.

    Args:
        settings: Optional application settings override. Defaults to
            the cached global settings when not provided.
        generation_client: Optional GroqClient override for the
            generator node, for testability.
        evaluation_client: Optional GroqClient override for the
            evaluator node, for testability.
        embedder: Optional embedding model override for the retriever
            node, for testability.
        retriever: Optional Chroma retriever override for the
            retriever node, for testability.

    Returns:
        CompiledStateGraph: The compiled, executable agent graph,
            executing Planner -> Retriever -> Generator -> Evaluator
            -> END sequentially, with no conditional branching.
    """
    active_settings = settings or get_settings()
    active_generation_client = generation_client or build_generation_client(
        active_settings
    )
    active_evaluation_client = evaluation_client or build_faithfulness_client(
        active_settings
    )

    graph = StateGraph(AgentState)

    graph.add_node("planner", make_planner_node())
    graph.add_node(
        "retriever",
        make_retriever_node(active_settings, embedder=embedder, retriever=retriever),
    )
    graph.add_node("generator", make_generator_node(active_generation_client))
    graph.add_node(
        "evaluator",
        make_evaluator_node(
            active_evaluation_client, active_settings.enable_evaluation
        ),
    )

    graph.set_entry_point("planner")
    graph.add_edge("planner", "retriever")
    graph.add_edge("retriever", "generator")
    graph.add_edge("generator", "evaluator")
    graph.add_edge("evaluator", END)

    return graph.compile()