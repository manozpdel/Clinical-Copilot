"""LangGraph graph construction for the Clinical Copilot agent.

This module is responsible ONLY for wiring node functions into a
compiled LangGraph graph. It contains no planning, retrieval,
generation, evaluation, or tool-execution logic; those live in their
respective modules and are only orchestrated here.

Execution flow:
    Planner -> Tool Router -> [Selected Tool | Retriever] -> Generator
    -> Evaluator -> END

`build_default_tool_router` is public so `streaming.service` can build
the same tool router without duplicating registration logic.
"""

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agent.nodes import (
    make_evaluator_node,
    make_generator_node,
    make_planner_node,
    make_retriever_node,
    make_tool_router_node,
)
from agent.state import AgentState
from app.core.config import Settings, get_settings
from ingest.embeddings import EmbeddingModel
from llm.client import GroqClient, build_faithfulness_client, build_generation_client
from rag.retriever import ChromaRetriever
from tools.ehr import EHRTool
from tools.mock_data import MOCK_PATIENTS
from tools.models import ToolName
from tools.notes import NotesTool
from tools.registry import ToolRegistry
from tools.router import ToolRouter
from tools.wearables import WearablesTool


def build_default_tool_router(settings: Settings) -> ToolRouter:
    """Build the default tool router with all mock clinical tools registered.

    Args:
        settings: Active application settings.

    Returns:
        ToolRouter: A router with the EHR, Notes, and Wearables tools
            registered against the shared mock patient population.
    """
    registry = ToolRegistry()
    registry.register(EHRTool())
    registry.register(NotesTool())
    registry.register(WearablesTool())

    return ToolRouter(
        registry=registry,
        known_patient_ids=set(MOCK_PATIENTS.keys()),
        max_retries=settings.max_tool_retries,
        retry_delay=settings.retry_delay,
        enable_validation=settings.enable_tool_validation,
    )


def _route_after_tool_selection(state: AgentState) -> str:
    """Decide which node runs after the tool router."""
    if state.get("selected_tool") == ToolName.RETRIEVAL.value:
        return "retriever"
    return "generator"


def build_graph(
    settings: Settings | None = None,
    generation_client: GroqClient | None = None,
    evaluation_client: GroqClient | None = None,
    embedder: EmbeddingModel | None = None,
    retriever: ChromaRetriever | None = None,
    tool_router: ToolRouter | None = None,
) -> CompiledStateGraph:
    """Build and compile the Clinical Copilot agent graph.

    Args:
        settings: Optional application settings override.
        generation_client: Optional GroqClient override for generation.
        evaluation_client: Optional GroqClient override for evaluation.
        embedder: Optional embedding model override.
        retriever: Optional Chroma retriever override.
        tool_router: Optional tool router override.

    Returns:
        CompiledStateGraph: The compiled, executable agent graph.
    """
    active_settings = settings or get_settings()
    active_generation_client = generation_client or build_generation_client(
        active_settings
    )
    active_evaluation_client = evaluation_client or build_faithfulness_client(
        active_settings
    )
    active_tool_router = tool_router or build_default_tool_router(active_settings)

    graph = StateGraph(AgentState)

    graph.add_node("planner", make_planner_node())
    graph.add_node(
        "tool_router",
        make_tool_router_node(active_tool_router),
    )
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
    graph.add_edge("planner", "tool_router")
    graph.add_conditional_edges(
        "tool_router",
        _route_after_tool_selection,
        {"retriever": "retriever", "generator": "generator"},
    )
    graph.add_edge("retriever", "generator")
    graph.add_edge("generator", "evaluator")
    graph.add_edge("evaluator", END)

    return graph.compile()
