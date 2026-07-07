"""Pydantic models used across the retrieval layer."""

from pydantic import BaseModel, Field


class RetrievedChunk(BaseModel):
    """A single retrieved document chunk with citation metadata.

    Attributes:
        chunk_id: Unique identifier of the chunk within its source
            document.
        patient_id: Identifier of the patient the chunk belongs to.
        source_file: Name of the file the chunk was extracted from.
        text: The chunk's text content.
        similarity: Normalized similarity score in the range (0, 1],
            where higher values indicate greater relevance.
    """

    chunk_id: str
    patient_id: str
    source_file: str
    text: str
    similarity: float = Field(..., ge=0.0, le=1.0)


class SearchResponse(BaseModel):
    """The result of running semantic search for a single query.

    Attributes:
        query: The original user query text.
        results: Retrieved chunks, ordered by descending similarity.
    """

    query: str
    results: list[RetrievedChunk]