"""Fixed-size text chunking with configurable overlap and metadata."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    """A single chunk of a source document.

    Attributes:
        chunk_id: Globally unique identifier for the chunk.
        text: The chunk's text content.
        metadata: Metadata associated with the chunk, including
            `patient_id`, `chunk_id`, and `source_file`.
    """

    chunk_id: str
    text: str
    metadata: dict[str, str]


def chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """Split text into fixed-size, overlapping word-based chunks.

    Args:
        text: The source text to split.
        chunk_size: Number of words per chunk.
        chunk_overlap: Number of overlapping words between consecutive
            chunks.

    Returns:
        list[str]: The resulting text chunks.

    Raises:
        ValueError: If `chunk_size` is not positive, or `chunk_overlap`
            is negative or greater than or equal to `chunk_size`.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be a positive integer.")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap must not be negative.")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size.")

    words = text.split()
    if not words:
        return []

    step = chunk_size - chunk_overlap
    chunks: list[str] = []
    start = 0

    while start < len(words):
        window = words[start : start + chunk_size]
        chunks.append(" ".join(window))

        if start + chunk_size >= len(words):
            break
        start += step

    return chunks


def chunk_document(
    text: str,
    patient_id: str,
    source_file: str,
    chunk_size: int,
    chunk_overlap: int,
) -> list[Chunk]:
    """Chunk a document and attach retrieval metadata to each chunk.

    Args:
        text: The full document text.
        patient_id: Identifier of the patient the document belongs to.
        source_file: Name of the source file the document was read from.
        chunk_size: Number of words per chunk.
        chunk_overlap: Number of overlapping words between consecutive
            chunks.

    Returns:
        list[Chunk]: Chunks of the document, each with attached metadata.
    """
    raw_chunks = chunk_text(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    chunks: list[Chunk] = []
    for index, chunk_value in enumerate(raw_chunks):
        chunk_id = f"{patient_id}_chunk_{index:03d}"
        metadata = {
            "patient_id": patient_id,
            "chunk_id": chunk_id,
            "source_file": source_file,
        }
        chunks.append(Chunk(chunk_id=chunk_id, text=chunk_value, metadata=metadata))

    return chunks