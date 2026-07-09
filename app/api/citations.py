"""Citation formatting diagnostic endpoint.

This module is responsible ONLY for the `/api/citations` routes. It
contains no retrieval or generation logic; it reuses the existing
citation formatter from `llm.citation` rather than reimplementing it.
"""

from fastapi import APIRouter

from llm.citation import extract_citations
from rag.models import RetrievedChunk

router = APIRouter(prefix="/citations", tags=["citations"])


@router.get("/example", response_model=list[str])
async def get_example_citations() -> list[str]:
    """Return an example of the citation format used across the API.

    Reuses the existing `llm.citation.extract_citations` formatter so
    the API layer never reimplements citation formatting logic.

    Returns:
        list[str]: A single example formatted citation string.
    """
    example_chunk = RetrievedChunk(
        chunk_id="patient_001_chunk_000",
        patient_id="patient_001",
        source_file="patient_001.txt",
        text="Patient is taking Metformin 500mg twice daily.",
        similarity=0.95,
    )
    return extract_citations([example_chunk])