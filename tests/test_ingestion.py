"""Tests for the embedding wrapper and full ingestion pipeline."""

from pathlib import Path

import pytest

from app.core.config import Settings
from ingest.embeddings import EmbeddingModel
from ingest.ingest import run_ingestion


def test_embedding_model_returns_vectors_for_each_text() -> None:
    """The embedding wrapper should return one vector per input text."""
    embedder = EmbeddingModel("BAAI/bge-small-en-v1.5")

    vectors = embedder.embed_documents(["hello world", "clinical note text"])

    assert len(vectors) == 2
    assert len(vectors[0]) > 0
    assert len(vectors[0]) == len(vectors[1])


@pytest.mark.slow
def test_run_ingestion_creates_expected_summary(tmp_path: Path) -> None:
    """Running the full pipeline should produce a consistent summary.

    This test downloads the FastEmbed model on first run and therefore
    requires network access.
    """
    settings = Settings(
        patient_count=2,
        chunk_size=50,
        chunk_overlap=10,
        collection_name="test_clinical_notes",
        data_raw_dir=tmp_path / "raw",
        data_processed_dir=tmp_path / "processed",
        chroma_path=tmp_path / "chroma_db",
    )

    summary = run_ingestion(settings)

    assert summary.patients_generated == 2
    assert summary.chunks_created > 0
    assert summary.embeddings_stored == summary.chunks_created
    assert summary.collection_name == "test_clinical_notes"
