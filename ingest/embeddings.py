"""Reusable embedding wrapper backed by FastEmbed."""

from fastembed import TextEmbedding


class EmbeddingModel:
    """A reusable wrapper around a FastEmbed text embedding model."""

    def __init__(self, model_name: str) -> None:
        """Initialize the embedding model.

        Args:
            model_name: Name of the FastEmbed embedding model to load,
                e.g. "BAAI/bge-small-en-v1.5".
        """
        self._model_name = model_name
        self._model = TextEmbedding(model_name=model_name)

    @property
    def model_name(self) -> str:
        """Return the name of the underlying embedding model.

        Returns:
            str: The embedding model name.
        """
        return self._model_name

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of documents.

        Args:
            texts: List of document texts to embed.

        Returns:
            list[list[float]]: One embedding vector per input text, in
                the same order.
        """
        return [vector.tolist() for vector in self._model.embed(texts)]

    def embed_query(self, text: str) -> list[float]:
        """Generate an embedding for a single query string.

        Args:
            text: Query text to embed.

        Returns:
            list[float]: The embedding vector for the query.
        """
        return self.embed_documents([text])[0]