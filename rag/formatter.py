"""Display formatting utilities for retrieved chunks and citations.

This module is responsible ONLY for turning retrieval results into
human-readable text. It contains no retrieval or business logic.
"""

from rag.models import RetrievedChunk

_SEPARATOR = "=" * 50
_DIVIDER = "-" * 50


def format_chunk(chunk: RetrievedChunk, rank: int) -> str:
    """Format a single retrieved chunk as a citation block.

    Args:
        chunk: The retrieved chunk to format.
        rank: 1-indexed rank of the chunk among the result set.

    Returns:
        str: A formatted, human-readable citation block.
    """
    return (
        f"{_SEPARATOR}\n"
        f"Rank: {rank}\n"
        f"Similarity: {chunk.similarity:.2f}\n"
        f"Patient ID: {chunk.patient_id}\n"
        f"Chunk ID: {chunk.chunk_id}\n"
        "\n"
        "Source:\n"
        f"{chunk.source_file}\n"
        f"{_DIVIDER}\n"
        "\n"
        f"{chunk.text}\n"
        f"{_SEPARATOR}"
    )


def format_results(chunks: list[RetrievedChunk]) -> str:
    """Format a list of retrieved chunks as sequential citation blocks.

    Args:
        chunks: Retrieved chunks to format, in display order.

    Returns:
        str: The concatenated, human-readable formatted output. Returns
            a friendly message when no chunks are provided.
    """
    if not chunks:
        return "No matching results found."

    blocks = [format_chunk(chunk, rank) for rank, chunk in enumerate(chunks, start=1)]
    return "\n\n".join(blocks)
