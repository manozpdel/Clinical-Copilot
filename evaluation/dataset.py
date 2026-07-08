"""Synthetic QA dataset generation for RAG evaluation.

QA pairs are derived directly from the structured synthetic patient
notes generated during ingestion, so that each question has a known
ground-truth patient, chunk, and citation.
"""

from pydantic import BaseModel

from app.core.config import Settings, get_settings
from ingest.chunker import Chunk, chunk_document
from ingest.utils import list_text_files, read_text_file

_SECTION_ORDER: tuple[str, ...] = (
    "Chief Complaint:",
    "Medical History:",
    "Medications:",
    "Allergies:",
    "Vital Signs:",
    "Assessment:",
    "Plan:",
)

_SECTION_QUESTIONS: tuple[tuple[str, str], ...] = (
    ("Medications:", "What medications is {patient_id} taking?"),
    ("Allergies:", "What allergies does {patient_id} have?"),
    ("Chief Complaint:", "What is the chief complaint for {patient_id}?"),
)


class QAItem(BaseModel):
    """A single synthetic question/answer evaluation pair.

    Attributes:
        question: The natural language question.
        expected_answer: The ground-truth answer text extracted from the
            source patient note.
        relevant_patient_id: Identifier of the patient the question is
            about.
        relevant_chunk_id: Identifier of the chunk that contains the
            ground-truth answer.
        ground_truth_citation: A human-readable citation string
            identifying the supporting patient, chunk, and source file.
    """

    question: str
    expected_answer: str
    relevant_patient_id: str
    relevant_chunk_id: str
    ground_truth_citation: str


def _extract_section(text: str, section_header: str) -> str | None:
    """Extract the body text of a named section from a patient note.

    Args:
        text: The full patient note text.
        section_header: The section header to extract, e.g.
            "Medications:".

    Returns:
        str | None: The section's body text, or None if the section
            header is not present.
    """
    if section_header not in text:
        return None

    start = text.index(section_header) + len(section_header)
    remainder = text[start:]

    next_positions = [
        remainder.index(header)
        for header in _SECTION_ORDER
        if header != section_header and header in remainder
    ]
    end = min(next_positions) if next_positions else len(remainder)

    return remainder[:end].strip()


def _find_chunk_for_section(
    chunks: list[Chunk], section_header: str
) -> Chunk | None:
    """Find the first chunk whose text contains a given section header.

    Args:
        chunks: Chunks produced from a single patient's note.
        section_header: The section header to search for.

    Returns:
        Chunk | None: The first matching chunk, or None if no chunk
            contains the section header.
    """
    for chunk in chunks:
        if section_header in chunk.text:
            return chunk
    return None


def _build_qa_item_for_section(
    patient_id: str,
    source_file: str,
    text: str,
    chunks: list[Chunk],
    section_header: str,
    question_template: str,
) -> QAItem | None:
    """Build a single QA item for one section of one patient note.

    Args:
        patient_id: Identifier of the patient the note belongs to.
        source_file: Name of the source file the note was read from.
        text: The full patient note text.
        chunks: Chunks produced from the patient note.
        section_header: The section header to base the question on.
        question_template: A format string accepting `patient_id`.

    Returns:
        QAItem | None: The constructed QA item, or None when the
            section or a supporting chunk could not be found.
    """
    section_text = _extract_section(text, section_header)
    chunk = _find_chunk_for_section(chunks, section_header)

    if not section_text or chunk is None:
        return None

    citation = f"Patient {patient_id}, Chunk {chunk.chunk_id}, {source_file}"

    return QAItem(
        question=question_template.format(patient_id=patient_id),
        expected_answer=section_text,
        relevant_patient_id=patient_id,
        relevant_chunk_id=chunk.chunk_id,
        ground_truth_citation=citation,
    )


def generate_qa_dataset(settings: Settings | None = None) -> list[QAItem]:
    """Generate a synthetic QA dataset from the ingested patient notes.

    Args:
        settings: Optional application settings override. Defaults to
            the cached global settings when not provided.

    Returns:
        list[QAItem]: The generated QA evaluation dataset.
    """
    active_settings = settings or get_settings()
    file_paths = list_text_files(active_settings.data_raw_dir)

    qa_items: list[QAItem] = []
    for file_path in file_paths:
        text = read_text_file(file_path)
        patient_id = file_path.stem
        chunks = chunk_document(
            text=text,
            patient_id=patient_id,
            source_file=file_path.name,
            chunk_size=active_settings.chunk_size,
            chunk_overlap=active_settings.chunk_overlap,
        )

        for section_header, question_template in _SECTION_QUESTIONS:
            qa_item = _build_qa_item_for_section(
                patient_id=patient_id,
                source_file=file_path.name,
                text=text,
                chunks=chunks,
                section_header=section_header,
                question_template=question_template,
            )
            if qa_item is not None:
                qa_items.append(qa_item)

    return qa_items