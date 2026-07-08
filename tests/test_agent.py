"""End-to-end tests for the compiled Clinical Copilot agent graph."""

from pathlib import Path

import chromadb

from agent.graph import build_graph
from agent.state import create_empty_state
from app.core.config import Settings
from rag.retriever import ChromaRetriever


class _FakeEmbedder:
    """A fake embedding model returning a fixed vector for any input."""

    def embed_query(self, text: str) -> list[float]:
        """Return a fixed embedding vector regardless of input text.

        Args:
            text: Query text to embed.

        Returns:
            list[float]: A fixed embedding vector.
        """
        return [1.0, 0.0, 0.0]


class _FakeGroqClient:
    """A fake GroqClient returning canned responses without network calls."""

    def __init__(self, response: str) -> None:
        """Initialize the fake client with a canned response.

        Args:
            response: The canned text to return from `generate`.
        """
        self._response = response

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Return the canned response, ignoring the prompts.

        Args:
            system_prompt: The system-level instructions for the model.
            user_prompt: The user-facing prompt content.

        Returns:
            str: The canned response.
        """
        return self._response


def _seed_collection(chroma_path: Path, collection_name: str) -> None:
    """Seed a Chroma collection with a single fixed-dimension test vector.

    Args:
        chroma_path: Directory in which to persist the Chroma database.
        collection_name: Name of the collection to create and seed.
    """
    client = chromadb.PersistentClient(path=str(chroma_path))
    collection = client.get_or_create_collection(name=collection_name)
    collection.upsert(
        ids=["patient_001_chunk_000"],
        documents=["Patient ID: patient_001\n\nMedications:\n- Metformin"],
        metadatas=[
            {
                "patient_id": "patient_001",
                "chunk_id": "patient_001_chunk_000",
                "source_file": "patient_001.txt",
            }
        ],
        embeddings=[[1.0, 0.0, 0.0]],
    )


def test_agent_graph_executes_all_stages_in_order(tmp_path: Path) -> None:
    """The full graph should run planner, retriever, generator, and evaluator."""
    chroma_path = tmp_path / "chroma_db"
    _seed_collection(chroma_path, "test_notes")

    settings = Settings(chroma_path=chroma_path, collection_name="test_notes")
    retriever = ChromaRetriever(settings)

    graph = build_graph(
        settings=settings,
        generation_client=_FakeGroqClient("Patient is taking Metformin."),
        evaluation_client=_FakeGroqClient("0.85"),
        embedder=_FakeEmbedder(),
        retriever=retriever,
    )

    initial_state = create_empty_state()
    initial_state["question"] = "What medications is patient_001 taking?"

    result = graph.invoke(initial_state)

    assert result["question"] == "What medications is patient_001 taking?"
    assert len(result["retrieved_chunks"]) == 1
    assert "Metformin" in result["formatted_context"]
    assert "Metformin" in result["answer"]
    assert "Citations:" in result["answer"]
    assert len(result["citations"]) == 1
    assert result["evaluation"]["faithfulness"] == 0.85
    assert result["evaluation"]["citation_present"] is True
    assert result["metadata"]["stage"] == "evaluated"