"""Retrieval logic for the Clinical Copilot agent.

This module is responsible ONLY for calling the existing retrieval
layer (Part 3) to embed the question, retrieve the top-K chunks, and
assemble them into a formatted context block. It contains no
generation or evaluation logic, and reuses `rag.search` and
`llm.prompts.build_context` rather than reimplementing them.
"""

from app.core.config import Settings
from ingest.embeddings import EmbeddingModel
from llm.prompts import build_context
from rag.models import RetrievedChunk
from rag.retriever import ChromaRetriever
from rag.search import search


def retrieve_context(
    question: str,
    settings: Settings,
    top_k: int | None = None,
    embedder: EmbeddingModel | None = None,
    retriever: ChromaRetriever | None = None,
) -> tuple[list[RetrievedChunk], str]:
    """Retrieve the top-K chunks for a question and assemble their context.

    Args:
        question: The normalized user question.
        settings: Active application settings.
        top_k: Optional override for the number of chunks to retrieve.
            Defaults to `settings.default_top_k` when not provided.
        embedder: Optional embedding model override, forwarded to the
            retrieval layer for testability.
        retriever: Optional Chroma retriever override, forwarded to the
            retrieval layer for testability.

    Returns:
        tuple[list[RetrievedChunk], str]: The retrieved chunks and
            their assembled formatted context.
    """
    effective_top_k = top_k if top_k is not None else settings.default_top_k
    query_settings = settings.model_copy(update={"top_k": effective_top_k})

    response = search(
        query=question,
        embedder=embedder,
        retriever=retriever,
        settings=query_settings,
    )
    context = build_context(response.results)

    return response.results, context
