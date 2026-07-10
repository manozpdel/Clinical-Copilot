"""Orchestration of the full data ingestion pipeline.

Generates synthetic patients, chunks their notes, produces embeddings,
and stores everything in a persistent Chroma collection.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import chromadb

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from ingest.chunker import Chunk, chunk_document
from ingest.embeddings import EmbeddingModel
from ingest.generator import generate_patient_records, save_patient_records
from ingest.utils import read_text_file

logger = get_logger(__name__)


@dataclass(frozen=True)
class IngestionSummary:
    """Summary of a completed ingestion run.

    Attributes:
        patients_generated: Number of synthetic patients generated.
        chunks_created: Total number of document chunks created.
        embeddings_stored: Total number of embeddings stored in Chroma.
        collection_name: Name of the Chroma collection written to.
    """

    patients_generated: int
    chunks_created: int
    embeddings_stored: int
    collection_name: str


def generate_and_save_patients(settings: Settings) -> list[Path]:
    """Generate synthetic patient records and persist them to disk.

    Args:
        settings: Active application settings.

    Returns:
        list[Path]: Paths to the written patient text files.
    """
    records = generate_patient_records(settings.patient_count)
    return save_patient_records(records, settings.data_raw_dir)


def build_chunks_from_files(file_paths: list[Path], settings: Settings) -> list[Chunk]:
    """Read patient files and split each into metadata-tagged chunks.

    Args:
        file_paths: Paths to patient text files.
        settings: Active application settings.

    Returns:
        list[Chunk]: All chunks produced across the given files.
    """
    chunks: list[Chunk] = []

    for file_path in sorted(file_paths):
        text = read_text_file(file_path)
        patient_id = file_path.stem
        document_chunks = chunk_document(
            text=text,
            patient_id=patient_id,
            source_file=file_path.name,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )
        chunks.extend(document_chunks)

    return chunks


def get_chroma_collection(settings: Settings) -> Any:
    """Get or create the persistent Chroma collection for clinical notes.

    Args:
        settings: Active application settings.

    Returns:
        Any: The Chroma collection instance.
    """
    client = chromadb.PersistentClient(path=str(settings.chroma_path))
    return client.get_or_create_collection(name=settings.collection_name)


def store_chunks(
    chunks: list[Chunk], embedder: EmbeddingModel, settings: Settings
) -> int:
    """Embed and upsert chunks into the persistent Chroma collection.

    Args:
        chunks: Chunks to embed and store.
        embedder: Embedding model wrapper used to generate vectors.
        settings: Active application settings.

    Returns:
        int: Number of chunks stored.
    """
    if not chunks:
        return 0

    collection = get_chroma_collection(settings)
    texts = [chunk.text for chunk in chunks]
    embeddings = embedder.embed_documents(texts)
    ids = [chunk.chunk_id for chunk in chunks]
    metadatas = [chunk.metadata for chunk in chunks]

    collection.upsert(
        ids=ids,
        documents=texts,
        metadatas=metadatas,
        embeddings=embeddings,
    )

    return len(chunks)


def run_ingestion(settings: Settings | None = None) -> IngestionSummary:
    """Run the full ingestion pipeline end to end.

    Generates synthetic patients, chunks their notes, embeds the
    chunks, and stores them in a persistent Chroma collection.

    Args:
        settings: Optional application settings override. Defaults to
            the cached global settings when not provided.

    Returns:
        IngestionSummary: Summary statistics for the ingestion run.
    """
    active_settings = settings or get_settings()
    logger.info("ingestion_started")

    saved_files = generate_and_save_patients(active_settings)
    logger.info("patients_generated", count=len(saved_files))

    chunks = build_chunks_from_files(saved_files, active_settings)
    logger.info("chunks_created", count=len(chunks))

    embedder = EmbeddingModel(active_settings.embedding_model)
    stored_count = store_chunks(chunks, embedder, active_settings)
    logger.info("embeddings_stored", count=stored_count)

    summary = IngestionSummary(
        patients_generated=len(saved_files),
        chunks_created=len(chunks),
        embeddings_stored=stored_count,
        collection_name=active_settings.collection_name,
    )
    logger.info("ingestion_completed", summary=summary.__dict__)

    return summary
