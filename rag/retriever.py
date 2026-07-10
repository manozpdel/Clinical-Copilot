"""Low-level Chroma communication for the retrieval layer.

This module is responsible ONLY for loading and querying the existing
persistent Chroma collection. It contains no business logic, scoring,
or formatting.
"""

from typing import Any

import chromadb

from app.core.config import Settings


class ChromaRetriever:
    """Wraps an existing persistent Chroma collection for vector search."""

    def __init__(self, settings: Settings) -> None:
        """Load the existing persistent Chroma collection.

        Args:
            settings: Application settings providing the Chroma path and
                collection name.
        """
        self._settings = settings
        self._client = chromadb.PersistentClient(path=str(settings.chroma_path))
        self._collection = self._client.get_or_create_collection(
            name=settings.collection_name
        )

    @property
    def collection_name(self) -> str:
        """Return the name of the loaded Chroma collection.

        Returns:
            str: The Chroma collection name.
        """
        return self._settings.collection_name

    def count(self) -> int:
        """Return the number of items stored in the collection.

        Returns:
            int: Number of stored items.
        """
        return self._collection.count()

    def query(self, query_embedding: list[float], top_k: int) -> dict[str, Any]:
        """Query the collection for the nearest chunks to an embedding.

        Args:
            query_embedding: Embedding vector representing the query.
            top_k: Maximum number of nearest results to retrieve.

        Returns:
            dict[str, Any]: Raw Chroma query response containing ids,
                documents, metadatas, and distances.
        """
        return self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
        )
