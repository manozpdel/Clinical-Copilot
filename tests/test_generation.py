"""Tests for RAG answer generation."""

from pathlib import Path

import chromadb

from app.core.config import Settings
from llm.generator import generate_answer
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
    """A fake ChatGroq client that returns a canned response."""

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Return a canned answer without making a network call.

        Args:
            system_prompt: The system-level instructions for the model.
            user_prompt: The user-facing prompt content.

        Returns:
            str: A canned response.
        """
        return "Patient is taking Metformin."


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
        documents=["Patient is taking Metformin 500mg twice daily."],
        metadatas=[
            {
                "patient_id": "patient_001",
                "chunk_id": "patient_001_chunk_000",
                "source_file": "patient_001.txt",
            }
        ],
        embeddings=[[1.0, 0.0, 0.0]],
    )


def test_generate_answer_includes_citations(tmp_path: Path) -> None:
    """The generated answer should include citations from retrieved chunks."""
    chroma_path = tmp_path / "chroma_db"
    _seed_collection(chroma_path, "test_notes")

    settings = Settings(chroma_path=chroma_path, collection_name="test_notes")
    retriever = ChromaRetriever(settings)

    result = generate_answer(
        question="What medications is the patient taking?",
        client=_FakeGroqClient(),
        embedder=_FakeEmbedder(),
        retriever=retriever,
        settings=settings,
    )

    assert "Metformin" in result.answer
    assert "Citations:" in result.answer
    assert len(result.citations) == 1
    assert result.context_chunks[0].patient_id == "patient_001"
    assert result.latency_seconds >= 0.0