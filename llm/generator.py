"""Answer generation for the Clinical Copilot RAG pipeline."""

import time

from pydantic import BaseModel

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from ingest.embeddings import EmbeddingModel
from llm.citation import append_citations, extract_citations
from llm.client import GroqClient, build_generation_client
from llm.prompts import build_prompt
from rag.models import RetrievedChunk
from rag.retriever import ChromaRetriever
from rag.search import search

logger = get_logger(__name__)


class GeneratedAnswer(BaseModel):
    """The result of running the full RAG generation pipeline.

    Attributes:
        question: The original user question.
        answer: The model-generated answer, with citations appended.
        citations: Formatted citation strings supporting the answer.
        context_chunks: The retrieved chunks used to build the context.
        latency_seconds: Wall-clock time taken to produce the answer.
    """

    question: str
    answer: str
    citations: list[str]
    context_chunks: list[RetrievedChunk]
    latency_seconds: float


def generate_answer(
    question: str,
    client: GroqClient | None = None,
    embedder: EmbeddingModel | None = None,
    retriever: ChromaRetriever | None = None,
    settings: Settings | None = None,
) -> GeneratedAnswer:
    """Run the full retrieval-augmented generation pipeline for a question.

    Args:
        question: The user's natural language question.
        client: Optional generation client override. Built from the
            generation API key/model in settings when not provided.
        embedder: Optional embedding model override, forwarded to
            retrieval.
        retriever: Optional Chroma retriever override, forwarded to
            retrieval.
        settings: Optional application settings override.

    Returns:
        GeneratedAnswer: The generated answer, citations, context
            chunks, and latency.
    """
    active_settings = settings or get_settings()
    active_client = client or build_generation_client(active_settings)

    start_time = time.monotonic()

    search_response = search(
        query=question,
        embedder=embedder,
        retriever=retriever,
        settings=active_settings,
    )
    chunks = search_response.results

    prompt = build_prompt(question=question, chunks=chunks)
    raw_answer = active_client.generate(
        system_prompt=prompt.system_prompt, user_prompt=prompt.user_prompt
    )

    citations = extract_citations(chunks)
    final_answer = append_citations(raw_answer, chunks)

    latency = time.monotonic() - start_time
    logger.info("answer_generated", question=question, latency_seconds=latency)

    return GeneratedAnswer(
        question=question,
        answer=final_answer,
        citations=citations,
        context_chunks=chunks,
        latency_seconds=latency,
    )