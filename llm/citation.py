"""Citation formatting for RAG-generated answers.

This module is responsible ONLY for formatting citations. It contains
no retrieval, prompt construction, or generation logic.
"""

from rag.models import RetrievedChunk


def format_citation(chunk: RetrievedChunk) -> str:
    """Format a single retrieved chunk as an inline citation string.

    Args:
        chunk: The retrieved chunk to cite.

    Returns:
        str: A formatted citation string, e.g. "[Citation: Patient
            patient_007, Chunk patient_007_chunk_003, patient_007.txt]".
    """
    return f"[Citation: Patient {chunk.patient_id}, Chunk {chunk.chunk_id}, {chunk.source_file}]"


def extract_citations(chunks: list[RetrievedChunk]) -> list[str]:
    """Format citations for every retrieved chunk.

    Args:
        chunks: Retrieved chunks to cite.

    Returns:
        list[str]: Formatted citation strings, one per chunk, in the
            same order as the input.
    """
    return [format_citation(chunk) for chunk in chunks]


def append_citations(answer: str, chunks: list[RetrievedChunk]) -> str:
    """Append a citations section to a generated answer.

    Args:
        answer: The raw model-generated answer text.
        chunks: Retrieved chunks supporting the answer.

    Returns:
        str: The answer with a trailing "Citations:" section listing
            each supporting chunk. Returns the answer unchanged when no
            chunks are provided.
    """
    citations = extract_citations(chunks)
    if not citations:
        return answer

    citation_block = "\n".join(citations)
    return f"{answer}\n\nCitations:\n{citation_block}"
