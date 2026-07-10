"""Voice query endpoint.

This module is responsible ONLY for the `/api/voice` route. Audio
transcription and agent execution are delegated to `VoiceService`;
persistence of the resulting conversation turn is delegated to
`database.crud.record_query_turn`. No business logic or raw SQL lives
here.
"""

import time

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from agent.graph import build_graph
from app.core.config import Settings, get_settings
from app.schemas.responses import VoiceResponse
from app.services.voice_service import VoiceService
from auth.dependencies import get_current_user
from database.crud import record_query_turn
from database.dependencies import get_db
from database.models import User
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
async def submit_voice(
    file: UploadFile = File(...),
    conversation_id: str | None = Form(default=None),
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
    service: VoiceService = Depends(get_voice_service),
) -> VoiceResponse:
    """Transcribe an uploaded audio file and answer it via the agent.

    Requires authentication. The resulting conversation turn is
    persisted under the authenticated user's account.

    Args:
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
            evaluation, and conversation/request identifiers.

    Raises:
        HTTPException: With status 413 if the upload exceeds the
            configured maximum size, or 422 if audio validation or
            transcription fails.
    """
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

    await record_query_turn(
        db,
        user_id=current_user.id,
        conversation_id=result["conversation_id"],
        query_text=result["transcript"],
        response_text=result["answer"],
        citations=result["citations"],
        evaluation=result["evaluation"],
        latency_ms=latency_ms,
    )

    return VoiceResponse(**result)
