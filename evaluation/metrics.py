"""Retrieval evaluation metrics for the RAG evaluation harness.

This module is responsible ONLY for pure metric calculations. It
contains no retrieval, generation, or LLM-judging logic.
"""


def recall_at_k(retrieved_chunk_ids: list[str], relevant_chunk_id: str) -> float:
    """Compute binary Recall@K for a single relevant chunk.

    Args:
        retrieved_chunk_ids: Chunk IDs retrieved for a query, already
            limited to the top K results.
        relevant_chunk_id: The ground-truth relevant chunk ID.

    Returns:
        float: 1.0 if the relevant chunk appears among the retrieved
            chunk IDs, otherwise 0.0.
    """
    return 1.0 if relevant_chunk_id in retrieved_chunk_ids else 0.0


def mean_reciprocal_rank(
    retrieved_chunk_ids: list[str], relevant_chunk_id: str
) -> float:
    """Compute the reciprocal rank of the relevant chunk in the results.

    Args:
        retrieved_chunk_ids: Chunk IDs retrieved for a query, ordered by
            descending relevance.
        relevant_chunk_id: The ground-truth relevant chunk ID.

    Returns:
        float: 1 / (rank of the relevant chunk, 1-indexed), or 0.0 if
            the relevant chunk was not retrieved.
    """
    for index, chunk_id in enumerate(retrieved_chunk_ids, start=1):
        if chunk_id == relevant_chunk_id:
            return 1.0 / index
    return 0.0