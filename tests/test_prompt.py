"""Tests for RAG prompt construction."""

from llm.prompts import build_context, build_prompt
from rag.models import RetrievedChunk


def _sample_chunk() -> RetrievedChunk:
    """Build a sample retrieved chunk for use in prompt tests.

    Returns:
        RetrievedChunk: A representative retrieved chunk.
    """
    return RetrievedChunk(
        chunk_id="patient_001_chunk_000",
        patient_id="patient_001",
        source_file="patient_001.txt",
        text="Patient is taking Metformin 500mg twice daily.",
        similarity=0.9,
    )


def test_build_context_includes_chunk_metadata() -> None:
    """The assembled context should preserve every chunk's metadata."""
    context = build_context([_sample_chunk()])

    assert "Patient ID: patient_001" in context
    assert "Chunk ID: patient_001_chunk_000" in context
    assert "Source File: patient_001.txt" in context
    assert "Metformin" in context


def test_build_context_handles_empty_chunks() -> None:
    """An empty chunk list should produce a friendly placeholder message."""
    context = build_context([])

    assert context == "No relevant context was retrieved."


def test_build_prompt_instructs_no_hallucination_and_citations() -> None:
    """The system prompt should forbid hallucination and require citations."""
    prompt = build_prompt(
        "What medications is the patient taking?", [_sample_chunk()]
    )

    assert "hallucinate" in prompt.system_prompt.lower()
    assert "cite" in prompt.system_prompt.lower()
    assert "What medications is the patient taking?" in prompt.user_prompt
    assert "Metformin" in prompt.user_prompt