"""Tests for fixed-size document chunking with overlap."""

from ingest.chunker import chunk_document, chunk_text


def test_chunk_text_respects_chunk_size() -> None:
    """All but the final chunk should contain exactly chunk_size words."""
    words = [f"word{i}" for i in range(100)]
    text = " ".join(words)

    chunks = chunk_text(text, chunk_size=20, chunk_overlap=5)

    assert len(chunks) > 1
    for chunk in chunks[:-1]:
        assert len(chunk.split()) == 20


def test_chunk_text_overlap_between_consecutive_chunks() -> None:
    """Consecutive chunks should share the configured overlap word count."""
    words = [f"word{i}" for i in range(50)]
    text = " ".join(words)

    chunks = chunk_text(text, chunk_size=10, chunk_overlap=4)

    first_chunk_words = chunks[0].split()
    second_chunk_words = chunks[1].split()
    overlap = set(first_chunk_words[-4:]) & set(second_chunk_words[:4])

    assert len(overlap) == 4


def test_chunk_document_metadata_is_preserved() -> None:
    """Chunk metadata should correctly reference the source document."""
    text = " ".join(f"word{i}" for i in range(30))

    chunks = chunk_document(
        text=text,
        patient_id="patient_001",
        source_file="patient_001.txt",
        chunk_size=10,
        chunk_overlap=2,
    )

    assert len(chunks) > 0
    for chunk in chunks:
        assert chunk.metadata["patient_id"] == "patient_001"
        assert chunk.metadata["source_file"] == "patient_001.txt"
        assert chunk.metadata["chunk_id"] == chunk.chunk_id