"""Tests for voice pipeline orchestration."""

from pathlib import Path

import chromadb
import pytest

from agent.graph import build_graph
from app.core.config import Settings
from rag.retriever import ChromaRetriever
from voice.audio import AudioValidationError
from voice.models import TranscriptionResult
from voice.pipeline import VoicePipeline
from voice.session import SessionManager
from voice.transcriber import Transcriber


class _FakeEmbedder:
    """A fake embedding model returning a fixed vector for any input."""

    def embed_query(self, text: str) -> list[float]:
        """Return a fixed embedding vector regardless of input text.

        Args:
            text: Query text to embed.

        Returns:
            list[float]: A fixed embedding vector.
        """
        return [1.0, 0.0, 0.0]


class _FakeGroqClient:
    """A fake GroqClient returning canned responses without network calls."""

    def __init__(self, response: str) -> None:
        """Initialize the fake client with a canned response.

        Args:
            response: The canned text to return from `generate`.
        """
        self._response = response

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Return the canned response, ignoring the prompts.

        Args:
            system_prompt: The system-level instructions for the model.
            user_prompt: The user-facing prompt content.

        Returns:
            str: The canned response.
        """
        return self._response


class _FakeTranscriber(Transcriber):
    """A fake transcriber returning a fixed transcription."""

    def __init__(self, text: str) -> None:
        """Initialize the fake transcriber.

        Args:
            text: The fixed text to return from `transcribe`.
        """
        self._text = text

    def transcribe(self, audio_bytes: bytes, filename: str) -> TranscriptionResult:
        """Return a fixed transcription result, ignoring the input audio.

        Args:
            audio_bytes: The raw audio file contents (unused).
            filename: Original filename (unused).

        Returns:
            TranscriptionResult: The fixed transcription result.
        """
        return TranscriptionResult(text=self._text, provider="fake", model="fake")


def _seed_collection(chroma_path: Path, collection_name: str) -> None:
    """Seed a Chroma collection with a single fixed-dimension test vector.

    Args:
        chroma_path: Directory in which to persist the Chroma database.
        collection_name: Name of the collection to create and seed.
    """
    client = chromadb.PersistentClient(path=str(chroma_path))
    collection = client.get_or_create_collection(name=collection_name)
    collection.upsert(
        ids=["patient_001_chunk_000"],
        documents=["Patient ID: patient_001\n\nMedications:\n- Metformin"],
        metadatas=[
            {
                "patient_id": "patient_001",
                "chunk_id": "patient_001_chunk_000",
                "source_file": "patient_001.txt",
            }
        ],
        embeddings=[[1.0, 0.0, 0.0]],
    )


def test_pipeline_raises_on_invalid_audio(tmp_path: Path) -> None:
    """The pipeline should surface audio validation failures."""
    settings = Settings(chroma_path=tmp_path / "chroma_db")
    graph = build_graph(
        settings=settings,
        generation_client=_FakeGroqClient("answer"),
        evaluation_client=_FakeGroqClient("0.9"),
        embedder=_FakeEmbedder(),
    )
    pipeline = VoicePipeline(
        settings=settings,
        transcriber=_FakeTranscriber("question"),
        graph=graph,
    )

    missing_audio = tmp_path / "missing.wav"

    with pytest.raises(AudioValidationError):
        pipeline.run(missing_audio)


def test_pipeline_runs_full_voice_turn(tmp_path: Path) -> None:
    """The pipeline should transcribe, run the agent, and record memory."""
    chroma_path = tmp_path / "chroma_db"
    _seed_collection(chroma_path, "test_notes")

    settings = Settings(chroma_path=chroma_path, collection_name="test_notes")
    retriever = ChromaRetriever(settings)

    graph = build_graph(
        settings=settings,
        generation_client=_FakeGroqClient("Patient is taking Metformin."),
        evaluation_client=_FakeGroqClient("0.85"),
        embedder=_FakeEmbedder(),
        retriever=retriever,
    )

    session_manager = SessionManager(max_history=10)
    pipeline = VoicePipeline(
        settings=settings,
        transcriber=_FakeTranscriber("What medications is patient_001 taking?"),
        graph=graph,
        session_manager=session_manager,
    )

    audio_path = tmp_path / "clip.wav"
    audio_path.write_bytes(b"RIFF" + b"\x00" * 40)

    result = pipeline.run(audio_path)

    assert result.transcript == "What medications is patient_001 taking?"
    assert "Metformin" in result.answer
    assert len(result.citations) == 1
    assert result.evaluation["faithfulness"] == 0.85
    assert len(result.history) == 2
    assert result.history[0].role == "user"
    assert result.history[1].role == "assistant"


def test_pipeline_reuses_conversation_across_turns(tmp_path: Path) -> None:
    """A second call with the same conversation_id should accumulate history."""
    chroma_path = tmp_path / "chroma_db"
    _seed_collection(chroma_path, "test_notes")

    settings = Settings(chroma_path=chroma_path, collection_name="test_notes")
    retriever = ChromaRetriever(settings)

    graph = build_graph(
        settings=settings,
        generation_client=_FakeGroqClient("Patient is taking Metformin."),
        evaluation_client=_FakeGroqClient("0.85"),
        embedder=_FakeEmbedder(),
        retriever=retriever,
    )

    session_manager = SessionManager(max_history=10)
    pipeline = VoicePipeline(
        settings=settings,
        transcriber=_FakeTranscriber("What medications is patient_001 taking?"),
        graph=graph,
        session_manager=session_manager,
    )

    audio_path = tmp_path / "clip.wav"
    audio_path.write_bytes(b"RIFF" + b"\x00" * 40)

    first_result = pipeline.run(audio_path)
    second_result = pipeline.run(audio_path, conversation_id=first_result.conversation_id)

    assert second_result.conversation_id == first_result.conversation_id
    assert len(second_result.history) == 4
