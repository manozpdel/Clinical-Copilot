"""Tests for StreamingService pipeline orchestration."""

from pathlib import Path

import chromadb
import pytest

from app.core.config import Settings
from database.base import Base
from database.models import User
from database.session import build_engine, build_session_factory
from rag.retriever import ChromaRetriever
from streaming.service import StreamingService
from tools.ehr import EHRTool
from tools.mock_data import MOCK_PATIENTS
from tools.registry import ToolRegistry
from tools.router import ToolRouter


class _FakeEmbedder:
    """A fake embedding model returning a fixed vector for any input."""

    def embed_query(self, text: str) -> list[float]:
        """Return a fixed embedding vector regardless of input text."""
        return [1.0, 0.0, 0.0]


class _FakeGroqClient:
    """A fake GroqClient supporting both generate() and generate_stream()."""

    def __init__(self, response: str) -> None:
        """Initialize with a canned response, split into word-level chunks."""
        self._response = response

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Return the canned response."""
        return self._response

    def generate_stream(self, system_prompt: str, user_prompt: str):
        """Yield the canned response word by word."""
        for word in self._response.split(" "):
            yield word + " "


@pytest.fixture
async def db_session():
    """Provide a fresh in-memory SQLite session with tables created."""
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:")
    engine = build_engine(settings)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    factory = build_session_factory(engine)
    async with factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def test_user(db_session):
    """Persist and return a test user."""
    user = User(email="stream-user@example.com", provider="local")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


def _seed_collection(chroma_path: Path, collection_name: str) -> None:
    """Seed a Chroma collection with a single fixed-dimension test vector."""
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


async def test_stream_query_emits_expected_event_sequence(
    tmp_path: Path, db_session, test_user
) -> None:
    """The pipeline should emit events in the correct order, ending in 'finished'."""
    chroma_path = tmp_path / "chroma_db"
    _seed_collection(chroma_path, "test_notes")

    settings = Settings(chroma_path=chroma_path, collection_name="test_notes")
    retriever = ChromaRetriever(settings)

    registry = ToolRegistry()
    registry.register(EHRTool())
    tool_router = ToolRouter(
        registry=registry, known_patient_ids=set(MOCK_PATIENTS.keys())
    )

    service = StreamingService(
        settings=settings,
        generation_client=_FakeGroqClient("Patient is taking Metformin."),
        evaluation_client=_FakeGroqClient("0.9"),
        embedder=_FakeEmbedder(),
        retriever=retriever,
        tool_router=tool_router,
    )

    events = [
        event
        async for event in service.stream_query(
            "What medications is patient_001 taking?", None, test_user.id, db_session
        )
    ]

    event_types = [event.event for event in events]

    assert event_types[0] == "node_start"
    assert "token" in event_types
    assert "citation" in event_types
    assert event_types[-1] == "finished"
    assert event_types.index("node_start") < event_types.index("finished")


async def test_stream_query_finished_event_contains_full_answer(
    tmp_path: Path, db_session, test_user
) -> None:
    """The finished event's answer should equal the concatenation of all tokens."""
    chroma_path = tmp_path / "chroma_db"
    _seed_collection(chroma_path, "test_notes")

    settings = Settings(chroma_path=chroma_path, collection_name="test_notes")
    retriever = ChromaRetriever(settings)

    registry = ToolRegistry()
    registry.register(EHRTool())
    tool_router = ToolRouter(
        registry=registry, known_patient_ids=set(MOCK_PATIENTS.keys())
    )

    service = StreamingService(
        settings=settings,
        generation_client=_FakeGroqClient("Patient is taking Metformin."),
        evaluation_client=_FakeGroqClient("0.9"),
        embedder=_FakeEmbedder(),
        retriever=retriever,
        tool_router=tool_router,
    )

    events = [
        event
        async for event in service.stream_query(
            "What medications is patient_001 taking?", None, test_user.id, db_session
        )
    ]

    finished = next(event for event in events if event.event == "finished")

    assert "Metformin" in finished.data["answer"]
    assert finished.data["query_id"]
