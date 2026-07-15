"""Server-Sent Events transport for the streaming agent pipeline.

This module is responsible ONLY for the `GET /stream/query` and
`POST /stream/voice` routes and the SSE wire-format response
generator, including heartbeats and disconnect handling. It contains
no pipeline orchestration logic (see `streaming.service`).

`/stream/voice` is deliberately `POST`, not `GET`: the browser's
native `EventSource` client used for true SSE cannot send a request
body, so it cannot upload audio. The frontend instead uses `fetch()`
with a streaming response reader for this endpoint, which still
receives the same `text/event-stream` payload.
"""

import asyncio
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from auth.dependencies import get_current_user, get_current_user_query_token
from database.dependencies import get_db
from database.models import User
from streaming.events import error_event, heartbeat_event
from streaming.schemas import StreamEvent
from streaming.serializers import to_sse
from streaming.service import StreamingService, build_streaming_service
from voice.audio import AudioValidationError, validate_audio_file
from voice.transcriber import GroqWhisperTranscriber, TranscriptionError

logger = get_logger(__name__)

router = APIRouter(prefix="/stream", tags=["streaming"])

_streaming_service_singleton: StreamingService | None = None


def get_streaming_service(settings: Settings = Depends(get_settings)) -> StreamingService:
    """Provide a lazily-constructed, process-wide StreamingService instance.

    Args:
        settings: Active application settings.

    Returns:
        StreamingService: The shared streaming service instance.
    """
    global _streaming_service_singleton
    if _streaming_service_singleton is None:
        _streaming_service_singleton = build_streaming_service(settings)
    return _streaming_service_singleton


async def _with_heartbeat(
    request: Request,
    event_generator: AsyncIterator[StreamEvent],
    heartbeat_interval: float,
) -> AsyncIterator[str]:
    """Merge a StreamEvent generator with periodic heartbeats and disconnect checks.

    Runs the event generator as a background task feeding an
    `asyncio.Queue`, so a heartbeat can still be emitted during long
    gaps between real events (e.g. while the evaluator's LLM-as-judge
    call is in flight).

    Args:
        request: The incoming HTTP request, polled for client
            disconnection.
        event_generator: The async generator of events to stream.
        heartbeat_interval: Seconds of inactivity before a heartbeat is
            sent.

    Yields:
        str: SSE-formatted text chunks, ready to write to the response
            body.
    """
    queue: asyncio.Queue = asyncio.Queue()

    async def _producer() -> None:
        try:
            async for event in event_generator:
                await queue.put(event)
        except Exception as error:  # noqa: BLE001
            await queue.put(error_event(str(error)))
        finally:
            await queue.put(None)

    producer_task = asyncio.create_task(_producer())

    try:
        while True:
            if await request.is_disconnected():
                logger.info("sse_client_disconnected")
                break

            try:
                event = await asyncio.wait_for(queue.get(), timeout=heartbeat_interval)
            except asyncio.TimeoutError:
                yield to_sse(heartbeat_event())
                continue

            if event is None:
                break

            yield to_sse(event)

            if event.event in ("finished", "error"):
                break
    finally:
        producer_task.cancel()


@router.get("/query")
async def stream_query_endpoint(
    request: Request,
    question: str,
    conversation_id: str | None = None,
    current_user: User = Depends(get_current_user_query_token),
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
    service: StreamingService = Depends(get_streaming_service),
) -> StreamingResponse:
    """Stream the agent's answer to a text question as Server-Sent Events.

    Authenticated via either an `Authorization: Bearer` header or a
    `?token=` query parameter, since the native `EventSource` client
    cannot set custom headers.

    Args:
        request: The incoming HTTP request.
        question: The user's natural language question.
        conversation_id: Optional existing conversation identifier.
        current_user: The authenticated user.
        settings: Active application settings.
        db: Request-scoped async database session.
        service: The streaming service.

    Returns:
        StreamingResponse: A `text/event-stream` response.

    Raises:
        HTTPException: With status 404 if streaming is disabled.
    """
    if not settings.enable_streaming:
        raise HTTPException(status_code=404, detail="Streaming is disabled.")

    generator = service.stream_query(question, conversation_id, current_user.id, db)
    return StreamingResponse(
        _with_heartbeat(request, generator, settings.stream_heartbeat_interval),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/voice")
async def stream_voice_endpoint(
    request: Request,
    file: UploadFile = File(...),
    conversation_id: str | None = None,
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
    service: StreamingService = Depends(get_streaming_service),
) -> StreamingResponse:
    """Transcribe uploaded audio, then stream the agent's answer as SSE.

    Args:
        request: The incoming HTTP request.
        file: The uploaded audio file (.wav, .mp3, or .m4a).
        conversation_id: Optional existing conversation identifier.
        current_user: The authenticated user.
        settings: Active application settings.
        db: Request-scoped async database session.
        service: The streaming service.

    Returns:
        StreamingResponse: A `text/event-stream` response.

    Raises:
        HTTPException: With status 404 if streaming is disabled, or 422
            if audio validation or transcription fails.
    """
    if not settings.enable_streaming:
        raise HTTPException(status_code=404, detail="Streaming is disabled.")

    audio_bytes = await file.read()

    import tempfile
    from pathlib import Path

    suffix = Path(file.filename or "audio.wav").suffix or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix) as temp_file:
        temp_file.write(audio_bytes)
        temp_file.flush()
        temp_path = Path(temp_file.name)

        try:
            validated_bytes = validate_audio_file(temp_path, settings.supported_audio_formats)
            transcriber = GroqWhisperTranscriber(settings)
            transcription = transcriber.transcribe(validated_bytes, filename=temp_path.name)
        except AudioValidationError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except TranscriptionError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    generator = service.stream_voice_query(
        transcription.text, conversation_id, current_user.id, db
    )
    return StreamingResponse(
        _with_heartbeat(request, generator, settings.stream_heartbeat_interval),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
