"""Streaming orchestration for the Clinical Copilot agent pipeline.

This module is responsible ONLY for running the agent pipeline
(planner -> tool router/retriever -> generator -> evaluator) as an
async generator of `StreamEvent`s, reusing the same pure functions the
non-streaming LangGraph nodes use (`agent.planner`, `agent.retriever_node`,
`agent.evaluator_node`, `agent.nodes.tool_output_to_chunk`,
`agent.graph.build_default_tool_router`) plus the streaming-capable
`GroqClient.generate_stream`. It contains no transport (SSE/WebSocket)
or DOM logic.
"""

import asyncio
import time
import uuid
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from agent.evaluator_node import evaluate_response
from agent.graph import build_default_tool_router
from agent.nodes import tool_output_to_chunk
from agent.planner import plan
from agent.retriever_node import retrieve_context
from app.core.config import Settings
from app.core.logging import get_logger
from database.crud import create_usage_log, record_query_turn
from ingest.embeddings import EmbeddingModel
from llm.citation import append_citations, extract_citations, format_citation
from llm.client import GroqClient, build_faithfulness_client, build_generation_client
from llm.prompts import build_context, build_prompt
from observability.logging import bind_request_context
from observability.metrics import record_llm_tokens
from rag.retriever import ChromaRetriever
from security.budget import estimate_usage
from security.quota import QuotaExceededError, check_quota_before_request
from streaming.events import (
    citation_event,
    error_event,
    evaluation_event,
    finished_event,
    node_complete_event,
    node_start_event,
    progress_event,
    token_event,
    tool_complete_event,
    tool_start_event,
)
from streaming.progress import ProgressTracker
from streaming.schemas import StreamEvent
from tools.models import ToolName
from tools.router import ToolRouter

logger = get_logger(__name__)

_STREAM_SENTINEL = object()


class StreamingService:
    """Runs one question through the agent pipeline, yielding StreamEvents."""

    def __init__(
        self,
        settings: Settings,
        generation_client: GroqClient,
        evaluation_client: GroqClient,
        embedder: EmbeddingModel | None = None,
        retriever: ChromaRetriever | None = None,
        tool_router: ToolRouter | None = None,
    ) -> None:
        """Initialize the streaming service.

        Args:
            settings: Active application settings.
            generation_client: GroqClient used for streamed answer
                generation.
            evaluation_client: GroqClient used for faithfulness
                judging.
            embedder: Optional embedding model override, for
                testability.
            retriever: Optional Chroma retriever override, for
                testability.
            tool_router: Optional tool router override, for
                testability.
        """
        self._settings = settings
        self._generation_client = generation_client
        self._evaluation_client = evaluation_client
        self._embedder = embedder
        self._retriever = retriever
        self._tool_router = tool_router or build_default_tool_router(settings)

    async def _stream_tokens(self, system_prompt: str, user_prompt: str) -> AsyncIterator[str]:
        """Adapt the synchronous `GroqClient.generate_stream` into an async generator.

        Each blocking `next()` call is offloaded to a thread executor
        so it doesn't block the event loop while waiting on network
        I/O.

        Args:
            system_prompt: The system-level instructions for the model.
            user_prompt: The user-facing prompt content.

        Yields:
            str: Successive text chunks as they arrive.
        """
        loop = asyncio.get_event_loop()
        iterator = self._generation_client.generate_stream(system_prompt, user_prompt)

        while True:
            chunk = await loop.run_in_executor(None, lambda: next(iterator, _STREAM_SENTINEL))
            if chunk is _STREAM_SENTINEL:
                break
            yield chunk

    async def _run_pipeline(
        self,
        question: str,
        transcript: str | None,
        conversation_id: str | None,
        user_id: uuid.UUID,
        db: AsyncSession,
    ) -> AsyncIterator[StreamEvent]:
        """Run planner -> context -> generator -> evaluator, yielding events throughout.

        Args:
            question: The (already normalized/transcribed) question to
                answer.
            transcript: The original voice transcript, if this pipeline
                run was triggered by `/stream/voice`; included in the
                final `finished` event when set.
            conversation_id: Optional existing conversation identifier.
            user_id: Identifier of the requesting user.
            db: Active async database session.

        Yields:
            StreamEvent: Every event produced over the course of the
                pipeline run, ending in either `finished` or `error`.
        """
        bind_request_context(user_id=str(user_id), endpoint="/stream/query", component="streaming")
        tracker = ProgressTracker()
        pipeline_start = time.monotonic()

        try:
            await check_quota_before_request(db, user_id, self._settings)
        except QuotaExceededError as error:
            yield error_event(str(error))
            return

        try:
            # --- Planner ---
            yield node_start_event("planner")
            node_start_time = time.monotonic()
            planned = plan(question=question, conversation_id=conversation_id)
            yield node_complete_event("planner", time.monotonic() - node_start_time)
            yield progress_event("planner", tracker.advance("planner"))

            resolved_conversation_id = planned["conversation_id"]
            request_id = planned["request_id"]
            normalized_question = planned["question"]

            # --- Tool routing / retrieval ---
            yield node_start_event("tool_router")
            node_start_time = time.monotonic()
            tool_result = self._tool_router.route(normalized_question)

            if tool_result.tool_name != ToolName.RETRIEVAL.value and tool_result.output is not None:
                yield tool_start_event(tool_result.tool_name, tool_result.patient_id)
                chunk = tool_output_to_chunk(
                    tool_name=tool_result.tool_name,
                    patient_id=tool_result.patient_id or "unknown",
                    data=tool_result.output.data,
                )
                chunks = [chunk]
                yield tool_complete_event(
                    tool_result.tool_name, True, time.monotonic() - node_start_time
                )
            else:
                chunks, _context = retrieve_context(
                    question=normalized_question,
                    settings=self._settings,
                    embedder=self._embedder,
                    retriever=self._retriever,
                )

            yield node_complete_event("tool_router", time.monotonic() - node_start_time)
            yield progress_event("context", tracker.advance("context"))

            context = build_context(chunks)
            for chunk in chunks:
                yield citation_event(
                    patient_id=chunk.patient_id,
                    chunk_id=chunk.chunk_id,
                    source_file=chunk.source_file,
                    similarity=chunk.similarity,
                    citation=format_citation(chunk),
                )

            # --- Generation (token streaming) ---
            yield node_start_event("generator")
            node_start_time = time.monotonic()
            prompt = build_prompt(question=normalized_question, chunks=chunks)

            raw_answer_parts: list[str] = []
            index = 0
            async for piece in self._stream_tokens(prompt.system_prompt, prompt.user_prompt):
                raw_answer_parts.append(piece)
                yield token_event(piece, index)
                index += 1

            raw_answer = "".join(raw_answer_parts)
            citations = extract_citations(chunks)
            final_answer = append_citations(raw_answer, chunks)
            record_llm_tokens(
                self._settings.generation_model,
                *_prompt_completion_token_estimate(prompt.user_prompt, raw_answer),
            )
            yield node_complete_event("generator", time.monotonic() - node_start_time)
            yield progress_event("generator", tracker.advance("generator"))

            # --- Evaluation ---
            yield node_start_event("evaluator")
            node_start_time = time.monotonic()
            yield evaluation_event("Calculating faithfulness...")

            loop = asyncio.get_event_loop()
            evaluation = await loop.run_in_executor(
                None,
                lambda: evaluate_response(
                    context=context,
                    answer=final_answer,
                    citations=citations,
                    client=self._evaluation_client,
                    enable_evaluation=self._settings.enable_evaluation,
                ),
            )

            yield evaluation_event("Generating metrics...", scores=evaluation)
            yield node_complete_event("evaluator", time.monotonic() - node_start_time)
            yield progress_event("evaluator", tracker.advance("evaluator"))

            # --- Persistence ---
            latency_seconds = time.monotonic() - pipeline_start
            usage = estimate_usage(
                model=self._settings.generation_model,
                prompt_text=prompt.user_prompt,
                completion_text=raw_answer,
            )
            conversation, query = await record_query_turn(
                db,
                user_id=user_id,
                conversation_id=resolved_conversation_id,
                query_text=transcript or normalized_question,
                response_text=final_answer,
                citations=citations,
                evaluation=evaluation,
                latency_ms=latency_seconds * 1000,
            )
            await create_usage_log(
                db,
                user_id=user_id,
                conversation_id=conversation.id,
                model=self._settings.generation_model,
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                cost_usd=usage.cost_usd,
                latency_ms=latency_seconds * 1000,
            )

            result: dict[str, Any] = {
                "answer": final_answer,
                "citations": citations,
                "evaluation": evaluation,
                "latency_seconds": latency_seconds,
                "conversation_id": str(resolved_conversation_id),
                "request_id": request_id,
                "query_id": str(query.id),
            }
            if transcript is not None:
                result["transcript"] = transcript

            yield finished_event(result)

        except Exception as error:  # noqa: BLE001
            logger.error("streaming_pipeline_failed", error=str(error))
            yield error_event(f"An error occurred while streaming: {error}")

    async def stream_query(
        self,
        question: str,
        conversation_id: str | None,
        user_id: uuid.UUID,
        db: AsyncSession,
    ) -> AsyncIterator[StreamEvent]:
        """Stream the full pipeline for a text question.

        Args:
            question: The user's natural language question.
            conversation_id: Optional existing conversation identifier.
            user_id: Identifier of the requesting user.
            db: Active async database session.

        Yields:
            StreamEvent: Every event produced over the course of the
                pipeline run.
        """
        async for event in self._run_pipeline(
            question=question,
            transcript=None,
            conversation_id=conversation_id,
            user_id=user_id,
            db=db,
        ):
            yield event

    async def stream_voice_query(
        self,
        transcript: str,
        conversation_id: str | None,
        user_id: uuid.UUID,
        db: AsyncSession,
    ) -> AsyncIterator[StreamEvent]:
        """Stream the full pipeline for an already-transcribed voice question.

        Transcription itself happens in `streaming.sse` before this is
        called (audio validation/transcription reuses `voice.audio`
        and `voice.transcriber` unchanged), so this method only
        prepends a `node_start`/`node_complete` pair for "transcriber"
        and then delegates to the same pipeline used for text queries.

        Args:
            transcript: The already-transcribed question text.
            conversation_id: Optional existing conversation identifier.
            user_id: Identifier of the requesting user.
            db: Active async database session.

        Yields:
            StreamEvent: Every event produced over the course of the
                pipeline run.
        """
        yield node_start_event("transcriber")
        yield node_complete_event("transcriber", 0.0)

        async for event in self._run_pipeline(
            question=transcript,
            transcript=transcript,
            conversation_id=conversation_id,
            user_id=user_id,
            db=db,
        ):
            yield event


def _prompt_completion_token_estimate(prompt_text: str, completion_text: str) -> tuple[int, int]:
    """Estimate prompt/completion token counts for metrics recording.

    Args:
        prompt_text: The text sent to the model.
        completion_text: The text generated by the model.

    Returns:
        tuple[int, int]: (prompt_tokens, completion_tokens), estimated
            via the same character-based heuristic used elsewhere.
    """
    from security.budget import estimate_tokens

    return estimate_tokens(prompt_text), estimate_tokens(completion_text)


def build_streaming_service(settings: Settings) -> StreamingService:
    """Build a production StreamingService backed by real Groq clients.

    Args:
        settings: Active application settings.

    Returns:
        StreamingService: A fully configured streaming service.
    """
    return StreamingService(
        settings=settings,
        generation_client=build_generation_client(settings),
        evaluation_client=build_faithfulness_client(settings),
    )
