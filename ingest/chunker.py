"""Section-aware document chunking with configurable overlap and metadata.

Patient notes have a fixed, known structure (a demographic header
followed by named clinical sections). Rather than splitting purely by
word count — which can cut a section in half across two chunks —
this module first splits on section boundaries, so each chunk holds a
complete section (or, for long sections, complete overlapping windows
within that single section). This keeps semantically related content
together and improves retrieval precision.
"""

from dataclasses import dataclass

_SECTION_HEADERS: tuple[str, ...] = (
    "Chief Complaint:",
    "Medical History:",
    "Medications:",
    "Allergies:",
    "Vital Signs:",
    "Assessment:",
    "Plan:",
)


@dataclass(frozen=True)
class Chunk:
    """A single chunk of a source document.

    Attributes:
        chunk_id: Globally unique identifier for the chunk.
        text: The chunk's text content, with the patient ID prepended
            so retrieval can match on identity even when a chunk's
            section content alone is generic.
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


def _split_into_sections(text: str) -> list[tuple[str, str]]:
    """Split a patient note into its demographic header and clinical sections.

    Args:
        text: The full patient note text.

    Returns:
        list[tuple[str, str]]: A list of (label, section_text) pairs,
            in document order. The first entry is always the
            demographic header, labeled "Header". Sections not present
            in the document are skipped.
    """
    present_headers = [
        header for header in _SECTION_HEADERS if header in text
    ]

    if not present_headers:
        return [("Header", text.strip())] if text.strip() else []

    first_header = present_headers[0]
    header_block = text[: text.index(first_header)].strip()

    sections: list[tuple[str, str]] = []
    if header_block:
        sections.append(("Header", header_block))

    for index, header in enumerate(present_headers):
        start = text.index(header) + len(header)
        if index + 1 < len(present_headers):
            end = text.index(present_headers[index + 1])
        else:
            end = len(text)

        body = text[start:end].strip()
        sections.append((header, f"{header}\n{body}"))

    return sections


def _prepend_patient_id(section_value: str, patient_id: str) -> str:
    """Prepend a patient ID header to a chunk's text.

    This ensures every chunk carries its patient identity in its stored
    text, not just the chunk containing the document's original header
    line. Without this, chunks covering generically-worded sections
    (e.g. medications, allergies) become indistinguishable across
    patients from the embedding model's perspective.

    Args:
        section_value: The raw section or sub-chunk text, without a
            patient ID header.
        patient_id: Identifier of the patient the chunk belongs to.

    Returns:
        str: The text with a "Patient ID: {patient_id}" header
            prepended.
    """
    return f"Patient ID: {patient_id}\n\n{section_value}"


def chunk_document(
    text: str,
    patient_id: str,
    source_file: str,
    chunk_size: int,
    chunk_overlap: int,
) -> list[Chunk]:
    """Chunk a document by section and attach retrieval metadata.

    The document is first split along its known clinical section
    boundaries so that each section's content stays together in a
    single chunk. Only sections that exceed `chunk_size` words are
    further split using fixed-size, overlapping windows. Every chunk's
    stored text has the patient ID prepended, so retrieval can identify
    the correct patient even for chunks whose section content is
    otherwise generic or structurally similar across different
    patients.

    Args:
        text: The full document text.
        patient_id: Identifier of the patient the document belongs to.
        source_file: Name of the source file the document was read from.
        chunk_size: Maximum number of words per chunk before a section
            is split further.
        chunk_overlap: Number of overlapping words between consecutive
            sub-chunks, for sections that exceed `chunk_size`.

    Returns:
        list[Chunk]: Chunks of the document, each with attached
            metadata and a prepended patient ID header.
    """
    sections = _split_into_sections(text)

    chunks: list[Chunk] = []
    chunk_index = 0

    for _label, section_value in sections:
        section_word_count = len(section_value.split())

        if section_word_count <= chunk_size:
            sub_chunks = [section_value]
        else:
            sub_chunks = chunk_text(
                section_value, chunk_size=chunk_size, chunk_overlap=chunk_overlap
            )

        for sub_chunk_value in sub_chunks:
            chunk_id = f"{patient_id}_chunk_{chunk_index:03d}"
            chunk_text_with_id = _prepend_patient_id(sub_chunk_value, patient_id)
            metadata = {
                "patient_id": patient_id,
                "chunk_id": chunk_id,
                "source_file": source_file,
            }
            chunks.append(
                Chunk(chunk_id=chunk_id, text=chunk_text_with_id, metadata=metadata)
            )
            chunk_index += 1

    return chunks