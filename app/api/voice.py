"""Voice query endpoint.

This module is responsible ONLY for the `/api/voice` route. Audio
transcription and agent execution are delegated to `VoiceService`; rate
limiting to `security.limiter`; quota enforcement to `security.quota`;
usage/cost calculation to `security.budget`; persistence to
`database.crud`; and observability (log context, token metrics) to
`observability`. No business logic or raw SQL lives here.
"""

import time

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from agent.graph import build_graph
from app.core.config import Settings, get_settings
from app.schemas.responses import VoiceResponse
from app.services.voice_service import VoiceService
from auth.dependencies import get_current_user
from database.crud import create_usage_log, record_query_turn
from database.dependencies import get_db
from database.models import User
from observability.logging import bind_request_context
from observability.metrics import record_llm_tokens
from security.budget import estimate_usage
from security.limiter import limiter, rate_limit_string
from security.quota import QuotaExceededError, check_quota_before_request
from voice.audio import AudioValidationError
from voice.pipeline import VoicePipeline
from voice.transcriber import GroqWhisperTranscriber, TranscriptionError

router = APIRouter(prefix="/voice", tags=["voice"])

_voice_service_singleton: VoiceService | None = None


def get_voice_service(settings: Settings = Depends(get_settings)) -> VoiceService:
    """Provide a lazily-constructed, process-wide VoiceService instance.

    Args:
        settings: Active application settings.

    Returns:
        VoiceService: The shared voice service instance, backed by the
            existing voice pipeline (transcriber + agent graph).
    """
    global _voice_service_singleton
    if _voice_service_singleton is None:
        graph = build_graph(settings)
        transcriber = GroqWhisperTranscriber(settings)
        pipeline = VoicePipeline(
            settings=settings, transcriber=transcriber, graph=graph
        )
        _voice_service_singleton = VoiceService(pipeline)
    return _voice_service_singleton


@router.post("", response_model=VoiceResponse)
@limiter.limit(rate_limit_string)
async def submit_voice(
    request: Request,
    file: UploadFile = File(...),
    conversation_id: str | None = Form(default=None),
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
    service: VoiceService = Depends(get_voice_service),
) -> VoiceResponse:
    """Transcribe an uploaded audio file and answer it via the agent.

    Requires authentication, is rate-limited, and enforces per-user
    daily request / monthly token / monthly cost quotas before invoking
    the pipeline. The resulting conversation turn and usage are
    persisted under the authenticated user's account, and the persisted
    query's ID is returned so the frontend can attach feedback/ratings
    to it.

    Args:
        request: The incoming HTTP request, required by the rate
            limiter's key function.
        file: The uploaded audio file (.wav, .mp3, or .m4a).
        conversation_id: Optional existing conversation identifier.
        current_user: The authenticated user, resolved from the bearer
            JWT.
        settings: Active application settings, used to enforce the
            maximum upload size.
        db: Request-scoped async database session.
        service: The voice service, injected via dependency override in
            tests or the default pipeline-backed service in production.

    Returns:
        VoiceResponse: The transcript, generated answer, citations,
            evaluation, conversation/request identifiers, and the
            persisted query ID.

    Raises:
        HTTPException: With status 413 if the upload exceeds the
            configured maximum size, 429 if the user's quota has been
            exceeded, or 422 if audio validation or transcription
            fails.
    """
    bind_request_context(
        user_id=str(current_user.id), endpoint="/api/voice", component="api"
    )

    try:
        await check_quota_before_request(db, current_user.id, settings)
    except QuotaExceededError as error:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(error)
        ) from error

    audio_bytes = await file.read()

    if len(audio_bytes) > settings.max_upload_size:
        raise HTTPException(
            status_code=413, detail="Audio file exceeds maximum upload size."
        )

    start_time = time.monotonic()
    try:
        result = service.run_voice(
            audio_bytes=audio_bytes,
            filename=file.filename or "audio.wav",
            conversation_id=conversation_id,
        )
    except AudioValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except TranscriptionError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    latency_ms = (time.monotonic() - start_time) * 1000

    usage = estimate_usage(
        model=settings.generation_model,
        prompt_text=result["transcript"],
        completion_text=result["answer"],
    )
    record_llm_tokens(settings.generation_model, usage.prompt_tokens, usage.completion_tokens)

    conversation, query = await record_query_turn(
        db,
        user_id=current_user.id,
        conversation_id=result["conversation_id"],
        query_text=result["transcript"],
        response_text=result["answer"],
        citations=result["citations"],
        evaluation=result["evaluation"],
        latency_ms=latency_ms,
    )

    await create_usage_log(
        db,
        user_id=current_user.id,
        conversation_id=conversation.id,
        model=settings.generation_model,
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
        cost_usd=usage.cost_usd,
        latency_ms=latency_ms,
    )

    return VoiceResponse(**result, query_id=str(query.id))
