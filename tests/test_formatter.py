"""Tests for citation formatting utilities."""

from rag.formatter import format_chunk, format_results
from rag.models import RetrievedChunk


def _sample_chunk() -> RetrievedChunk:
    """Build a sample retrieved chunk for use in formatter tests.

    Returns:
        RetrievedChunk: A representative retrieved chunk.
    """
    return RetrievedChunk(
        chunk_id="patient_007_chunk_003",
        patient_id="patient_007",
        source_file="patient_007.txt",
        text="Patient reports chest pain for three days.",
        similarity=0.92,
    )


def test_format_chunk_includes_all_fields() -> None:
    """A formatted chunk should include rank, similarity, and citation metadata."""
    formatted = format_chunk(_sample_chunk(), rank=1)

    assert "Rank: 1" in formatted
    assert "Similarity: 0.92" in formatted
    assert "Patient ID: patient_007" in formatted
    assert "Chunk ID: patient_007_chunk_003" in formatted
    assert "patient_007.txt" in formatted
    assert "Patient reports chest pain for three days." in formatted


def test_format_results_with_multiple_chunks() -> None:
    """Multiple chunks should be formatted as sequential, ranked blocks."""
    chunks = [_sample_chunk(), _sample_chunk()]

    formatted = format_results(chunks)

    assert "Rank: 1" in formatted
    assert "Rank: 2" in formatted


def test_format_results_with_no_chunks_returns_friendly_message() -> None:
    """An empty result list should produce a friendly no-results message."""
    formatted = format_results([])

    assert formatted == "No matching results found."
