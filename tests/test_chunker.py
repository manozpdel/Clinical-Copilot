"""Tests for section-aware document chunking with overlap."""

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


def _sample_note() -> str:
    """Build a small, realistically structured patient note.

    Returns:
        str: A patient note text spanning several clinical sections.
    """
    return (
        "Patient ID: patient_003\n"
        "Name: Jane Doe\n"
        "Age: 45\n"
        "Sex: Female\n\n"
        "Chief Complaint:\n"
        "Persistent cough\n\n"
        "Medications:\n"
        "- Metformin 500mg twice daily\n"
        "- Lisinopril 10mg daily\n\n"
        "Allergies:\n"
        "- Penicillin\n"
    )


def test_chunk_document_metadata_is_preserved() -> None:
    """Chunk metadata should correctly reference the source document."""
    chunks = chunk_document(
        text=_sample_note(),
        patient_id="patient_003",
        source_file="patient_003.txt",
        chunk_size=200,
        chunk_overlap=20,
    )

    assert len(chunks) > 0
    for chunk in chunks:
        assert chunk.metadata["patient_id"] == "patient_003"
        assert chunk.metadata["source_file"] == "patient_003.txt"
        assert chunk.metadata["chunk_id"] == chunk.chunk_id


def test_chunk_document_prepends_patient_id_to_every_chunk() -> None:
    """Every chunk's stored text should carry the patient ID header."""
    chunks = chunk_document(
        text=_sample_note(),
        patient_id="patient_003",
        source_file="patient_003.txt",
        chunk_size=200,
        chunk_overlap=20,
    )

    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.text.startswith("Patient ID: patient_003")


def test_chunk_document_keeps_each_section_in_one_chunk() -> None:
    """A section that fits within chunk_size should not be split apart."""
    chunks = chunk_document(
        text=_sample_note(),
        patient_id="patient_003",
        source_file="patient_003.txt",
        chunk_size=200,
        chunk_overlap=20,
    )

    medication_chunks = [chunk for chunk in chunks if "Metformin" in chunk.text]

    assert len(medication_chunks) == 1
    assert "Lisinopril" in medication_chunks[0].text
    assert "Penicillin" not in medication_chunks[0].text


def test_chunk_document_splits_oversized_section(monkeypatch=None) -> None:
    """A section exceeding chunk_size should be split into sub-chunks."""
    long_medication_list = "\n".join(
        f"- Medication{i} 10mg daily" for i in range(40)
    )
    text = (
        "Patient ID: patient_009\n\n"
        "Medications:\n"
        f"{long_medication_list}\n"
    )

    chunks = chunk_document(
        text=text,
        patient_id="patient_009",
        source_file="patient_009.txt",
        chunk_size=20,
        chunk_overlap=5,
    )

    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.text.startswith("Patient ID: patient_009")