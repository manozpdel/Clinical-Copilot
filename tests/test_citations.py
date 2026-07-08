"""Tests for citation formatting utilities."""

from llm.citation import append_citations, extract_citations, format_citation
from rag.models import RetrievedChunk


def _sample_chunk() -> RetrievedChunk:
    """Build a sample retrieved chunk for use in citation tests.

    Returns:
        RetrievedChunk: A representative retrieved chunk.
    """
    return RetrievedChunk(
        chunk_id="patient_007_chunk_003",
        patient_id="patient_007",
        source_file="patient_007.txt",
        text="Patient is taking Metformin.",
        similarity=0.95,
    )


def test_format_citation_contains_required_fields() -> None:
    """A formatted citation should reference patient, chunk, and source."""
    citation = format_citation(_sample_chunk())

    assert "patient_007" in citation
    assert "patient_007_chunk_003" in citation
    assert "patient_007.txt" in citation


def test_extract_citations_returns_one_per_chunk() -> None:
    """Extracting citations should produce one citation per chunk."""
    citations = extract_citations([_sample_chunk(), _sample_chunk()])

    assert len(citations) == 2


def test_append_citations_adds_citations_section() -> None:
    """Appending citations should add a trailing Citations section."""
    answer = "Patient is taking Metformin."

    result = append_citations(answer, [_sample_chunk()])

    assert answer in result
    assert "Citations:" in result
    assert "patient_007_chunk_003" in result


def test_append_citations_with_no_chunks_returns_unchanged_answer() -> None:
    """With no supporting chunks, the answer should be returned unchanged."""
    answer = "No information available."

    result = append_citations(answer, [])

    assert result == answer