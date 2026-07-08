"""Tests for individual agent node domain logic."""

from pathlib import Path

import chromadb
import pytest

from agent.evaluator_node import evaluate_response
from agent.generator_node import generate_response
from agent.planner import plan
from agent.retriever_node import retrieve_context
from app.core.config import Settings
from rag.models import RetrievedChunk
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

    def __init__(self, response: str = "Patient is taking Metformin.") -> None:
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


def test_plan_normalizes_whitespace_and_generates_ids() -> None:
    """Planning should normalize whitespace and generate missing identifiers."""
    state = plan("  What   medications   is patient_001 taking?  ")

    assert state["question"] == "What medications is patient_001 taking?"
    assert state["conversation_id"]
    assert state["request_id"]
    assert state["metadata"]["stage"] == "planned"


def test_plan_raises_on_empty_question() -> None:
    """Planning should reject an empty or whitespace-only question."""
    with pytest.raises(ValueError):
        plan("   ")


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


def test_retrieve_context_returns_chunks_and_formatted_context(
    tmp_path: Path,
) -> None:
    """The retriever node should return chunks and a matching context block."""
    chroma_path = tmp_path / "chroma_db"
    _seed_collection(chroma_path, "test_notes")

    settings = Settings(chroma_path=chroma_path, collection_name="test_notes")
    retriever = ChromaRetriever(settings)

    chunks, context = retrieve_context(
        question="What medications is patient_001 taking?",
        settings=settings,
        embedder=_FakeEmbedder(),
        retriever=retriever,
    )

    assert len(chunks) == 1
    assert chunks[0].patient_id == "patient_001"
    assert "patient_001" in context
    assert "Metformin" in context


def test_generate_response_includes_citations() -> None:
    """The generator node should append citations to the raw answer."""
    chunk = RetrievedChunk(
        chunk_id="patient_001_chunk_000",
        patient_id="patient_001",
        source_file="patient_001.txt",
        text="Patient is taking Metformin.",
        similarity=0.9,
    )

    answer, citations, prompt = generate_response(
        question="What medications is patient_001 taking?",
        chunks=[chunk],
        client=_FakeGroqClient(),
    )

    assert "Citations:" in answer
    assert len(citations) == 1
    assert "patient_001" in prompt.user_prompt


def test_evaluate_response_with_evaluation_enabled() -> None:
    """The evaluator node should score faithfulness when evaluation is enabled."""
    evaluation = evaluate_response(
        context="Patient ID: patient_001\n\nMedications:\n- Metformin",
        answer="Patient is taking Metformin.",
        citations=["[Citation: Patient patient_001, Chunk c1, patient_001.txt]"],
        client=_FakeGroqClient(response="0.9"),
        enable_evaluation=True,
    )

    assert evaluation["faithfulness"] == 0.9
    assert evaluation["citation_present"] is True
    assert evaluation["context_used"] is True


def test_evaluate_response_with_evaluation_disabled() -> None:
    """The evaluator node should skip the LLM judge when evaluation is disabled."""
    evaluation = evaluate_response(
        context="Some context",
        answer="Some answer",
        citations=[],
        client=_FakeGroqClient(),
        enable_evaluation=False,
    )

    assert evaluation["faithfulness"] is None
    assert evaluation["citation_present"] is False
    assert evaluation["context_used"] is False