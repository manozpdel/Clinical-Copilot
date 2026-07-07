"""Tests for semantic search business logic."""

from pathlib import Path

import chromadb
import pytest

from app.core.config import Settings
from ingest.embeddings import EmbeddingModel
from rag.retriever import ChromaRetriever
from rag.search import embed_query, retrieve, search


def _seed_fixed_vector_collection(chroma_path: Path, collection_name: str) -> None:
    """Seed a Chroma collection with a single fixed-dimension test vector.

    Args:
        chroma_path: Directory in which to persist the Chroma database.
        collection_name: Name of the collection to create and seed.
    """
    client = chromadb.PersistentClient(path=str(chroma_path))
    collection = client.get_or_create_collection(name=collection_name)
    collection.upsert(
        ids=["patient_001_chunk_000"],
        documents=["Patient reports chest pain for three days."],
        metadatas=[
            {
                "patient_id": "patient_001",
                "chunk_id": "patient_001_chunk_000",
                "source_file": "patient_001.txt",
            }
        ],
        embeddings=[[1.0, 0.0, 0.0]],
    )


def test_retrieve_returns_ranked_chunks(tmp_path: Path) -> None:
    """Retrieve should convert raw Chroma results into RetrievedChunk objects."""
    chroma_path = tmp_path / "chroma_db"
    _seed_fixed_vector_collection(chroma_path, "test_notes")

    settings = Settings(chroma_path=chroma_path, collection_name="test_notes")
    retriever = ChromaRetriever(settings)

    chunks = retrieve(
        query_embedding=[1.0, 0.0, 0.0],
        retriever=retriever,
        top_k=5,
        min_similarity_score=0.0,
        max_results=10,
    )

    assert len(chunks) == 1
    assert chunks[0].patient_id == "patient_001"
    assert chunks[0].chunk_id == "patient_001_chunk_000"
    assert chunks[0].source_file == "patient_001.txt"
    assert 0.0 < chunks[0].similarity <= 1.0


def test_retrieve_filters_by_min_similarity_score(tmp_path: Path) -> None:
    """Retrieve should exclude chunks below the minimum similarity threshold."""
    chroma_path = tmp_path / "chroma_db"
    _seed_fixed_vector_collection(chroma_path, "test_notes")

    settings = Settings(chroma_path=chroma_path, collection_name="test_notes")
    retriever = ChromaRetriever(settings)

    chunks = retrieve(
        query_embedding=[1.0, 0.0, 0.0],
        retriever=retriever,
        top_k=5,
        min_similarity_score=1.5,
        max_results=10,
    )

    assert chunks == []


def test_retrieve_handles_empty_collection(tmp_path: Path) -> None:
    """Retrieve should return an empty list when the collection has no data."""
    chroma_path = tmp_path / "chroma_db"
    settings = Settings(chroma_path=chroma_path, collection_name="empty_notes")
    retriever = ChromaRetriever(settings)

    chunks = retrieve(
        query_embedding=[1.0, 0.0, 0.0],
        retriever=retriever,
        top_k=5,
        min_similarity_score=0.0,
        max_results=10,
    )

    assert chunks == []


@pytest.mark.slow
def test_embed_query_returns_vector() -> None:
    """Embedding a query should return a non-empty float vector."""
    embedder = EmbeddingModel("BAAI/bge-small-en-v1.5")

    vector = embed_query("chest pain", embedder)

    assert len(vector) > 0


@pytest.mark.slow
def test_search_end_to_end(tmp_path: Path) -> None:
    """The full search pipeline should embed, retrieve, and return results.

    This test downloads the FastEmbed model on first run and therefore
    requires network access.
    """
    chroma_path = tmp_path / "chroma_db"
    embedder = EmbeddingModel("BAAI/bge-small-en-v1.5")
    seed_text = "Patient reports chest pain for three days."
    seed_vector = embedder.embed_documents([seed_text])[0]

    client = chromadb.PersistentClient(path=str(chroma_path))
    collection = client.get_or_create_collection(name="test_notes")
    collection.upsert(
        ids=["patient_001_chunk_000"],
        documents=[seed_text],
        metadatas=[
            {
                "patient_id": "patient_001",
                "chunk_id": "patient_001_chunk_000",
                "source_file": "patient_001.txt",
            }
        ],
        embeddings=[seed_vector],
    )

    settings = Settings(chroma_path=chroma_path, collection_name="test_notes")
    response = search(query="chest pain", settings=settings)

    assert response.query == "chest pain"
    assert len(response.results) >= 1