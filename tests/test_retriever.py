"""Tests for the low-level Chroma retriever."""

from pathlib import Path

import chromadb

from app.core.config import Settings
from rag.retriever import ChromaRetriever


def _seed_collection(chroma_path: Path, collection_name: str) -> None:
    """Seed a Chroma collection with two fixed-dimension test vectors.

    Args:
        chroma_path: Directory in which to persist the Chroma database.
        collection_name: Name of the collection to create and seed.
    """
    client = chromadb.PersistentClient(path=str(chroma_path))
    collection = client.get_or_create_collection(name=collection_name)
    collection.upsert(
        ids=["patient_001_chunk_000", "patient_002_chunk_000"],
        documents=["Patient reports chest pain.", "Patient reports headache."],
        metadatas=[
            {
                "patient_id": "patient_001",
                "chunk_id": "patient_001_chunk_000",
                "source_file": "patient_001.txt",
            },
            {
                "patient_id": "patient_002",
                "chunk_id": "patient_002_chunk_000",
                "source_file": "patient_002.txt",
            },
        ],
        embeddings=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
    )


def test_chroma_retriever_loads_existing_collection(tmp_path: Path) -> None:
    """The retriever should load an existing collection without recreating it."""
    chroma_path = tmp_path / "chroma_db"
    _seed_collection(chroma_path, "test_notes")

    settings = Settings(chroma_path=chroma_path, collection_name="test_notes")
    retriever = ChromaRetriever(settings)

    assert retriever.count() == 2
    assert retriever.collection_name == "test_notes"


def test_chroma_retriever_query_returns_nearest_neighbor(tmp_path: Path) -> None:
    """A query close to a stored vector should retrieve it as the top result."""
    chroma_path = tmp_path / "chroma_db"
    _seed_collection(chroma_path, "test_notes")

    settings = Settings(chroma_path=chroma_path, collection_name="test_notes")
    retriever = ChromaRetriever(settings)

    results = retriever.query(query_embedding=[1.0, 0.0, 0.0], top_k=1)

    assert results["ids"][0][0] == "patient_001_chunk_000"
