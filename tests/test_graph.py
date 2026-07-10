"""Tests for agent graph construction."""

from agent.graph import build_graph
from app.core.config import Settings


class _FakeGroqClient:
    """A fake GroqClient used only to avoid real network calls at build time."""

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Return a canned response.

        Args:
            system_prompt: The system-level instructions for the model.
            user_prompt: The user-facing prompt content.

        Returns:
            str: A canned response.
        """
        return "canned response"


def test_build_graph_compiles_successfully() -> None:
    """The graph should build and compile without error using injected clients."""
    settings = Settings()

    graph = build_graph(
        settings=settings,
        generation_client=_FakeGroqClient(),
        evaluation_client=_FakeGroqClient(),
    )

    assert graph is not None


def test_build_graph_contains_expected_nodes() -> None:
    """The compiled graph should contain exactly the four pipeline nodes."""
    settings = Settings()

    graph = build_graph(
        settings=settings,
        generation_client=_FakeGroqClient(),
        evaluation_client=_FakeGroqClient(),
    )

    node_names = set(graph.get_graph().nodes.keys())

    assert "planner" in node_names
    assert "retriever" in node_names
    assert "generator" in node_names
    assert "evaluator" in node_names
