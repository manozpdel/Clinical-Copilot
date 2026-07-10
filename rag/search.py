"""Business logic for embedding queries and performing semantic search.

This module contains the reusable `search`, `retrieve`, and
`embed_query` functions. These interfaces are intentionally kept clean
and free of I/O formatting concerns so they can later be reused by
FastAPI, LangGraph, evaluation, and LLM-based components.
"""

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from ingest.embeddings import EmbeddingModel
from rag.models import RetrievedChunk, SearchResponse
from rag.retriever import ChromaRetriever

logger = get_logger(__name__)


def _distance_to_similarity(distance: float) -> float:
    """Convert a Chroma distance value into a bounded similarity score.

    Args:
        distance: Raw distance returned by Chroma (smaller is more
            similar).

    Returns:
        float: A similarity score in the range (0, 1], monotonically
            decreasing with distance.
    """
    return 1.0 / (1.0 + max(distance, 0.0))


def embed_query(query: str, embedder: EmbeddingModel) -> list[float]:
    """Embed a user query using the shared embedding model.

    Args:
        query: Raw user query text.
        embedder: Embedding model wrapper, matching the model used
            during ingestion.

    Returns:
        list[float]: Embedding vector for the query.
    """
    return embedder.embed_query(query)


def retrieve(
    query_embedding: list[float],
    retriever: ChromaRetriever,
    top_k: int,
    min_similarity_score: float,
    max_results: int,
) -> list[RetrievedChunk]:
    """Retrieve and filter the nearest chunks for a query embedding.

    Args:
        query_embedding: Embedding vector representing the query.
        retriever: Chroma retriever instance to query.
        top_k: Number of nearest neighbors to request from Chroma.
        min_similarity_score: Minimum similarity score a result must
            have to be included.
        max_results: Maximum number of results to return after
            filtering.

    Returns:
        list[RetrievedChunk]: Retrieved chunks, ordered by descending
            similarity, filtered and capped.
    """
    raw_results = retriever.query(query_embedding, top_k=top_k)

    ids = raw_results.get("ids", [[]])[0]
    documents = raw_results.get("documents", [[]])[0]
    metadatas = raw_results.get("metadatas", [[]])[0]
    distances = raw_results.get("distances", [[]])[0]

    chunks: list[RetrievedChunk] = []
    for chunk_id, document, metadata, distance in zip(
        ids, documents, metadatas, distances, strict=True
    ):
        similarity = _distance_to_similarity(distance)
        if similarity < min_similarity_score:
            continue
        chunks.append(
            RetrievedChunk(
                chunk_id=metadata.get("chunk_id", chunk_id),
                patient_id=metadata.get("patient_id", "unknown"),
                source_file=metadata.get("source_file", "unknown"),
                text=document,
                similarity=similarity,
            )
        )

    return chunks[:max_results]


def search(
    query: str,
    embedder: EmbeddingModel | None = None,
    retriever: ChromaRetriever | None = None,
    settings: Settings | None = None,
) -> SearchResponse:
    """Run the full semantic search pipeline for a user query.

    Args:
        query: Raw user query text.
        embedder: Optional embedding model override. A new instance is
            created from settings when not provided.
        retriever: Optional Chroma retriever override. A new instance is
            created from settings when not provided.
        settings: Optional application settings override. Defaults to
            the cached global settings when not provided.

    Returns:
        SearchResponse: The query along with its retrieved chunks.
    """
    active_settings = settings or get_settings()
    active_embedder = embedder or EmbeddingModel(active_settings.embedding_model)
    active_retriever = retriever or ChromaRetriever(active_settings)

    logger.info("search_started", query=query)
    query_embedding = embed_query(query, active_embedder)

    results = retrieve(
        query_embedding=query_embedding,
        retriever=active_retriever,
        top_k=active_settings.top_k,
        min_similarity_score=active_settings.min_similarity_score,
        max_results=active_settings.max_results,
    )
    logger.info("search_completed", query=query, result_count=len(results))

    return SearchResponse(query=query, results=results)
