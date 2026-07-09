"""Business logic for the voice query REST endpoint.

This module is responsible ONLY for adapting an uploaded audio payload
into the existing voice pipeline (Part 7) and shaping the result for
the API layer. It contains no FastAPI routing, request validation, or
pipeline-construction logic of its own.
"""

import tempfile
from pathlib import Path
from typing import Any

from app.core.logging import get_logger
from voice.pipeline import VoicePipeline

logger = get_logger(__name__)


class VoiceService:
    """Runs an uploaded audio file through the existing voice pipeline."""

    def __init__(self, pipeline: VoicePipeline) -> None:
        """Initialize the voice service.

        Args:
            pipeline: The voice pipeline instance, reused unchanged
                from Part 7.
        """
        self._pipeline = pipeline

    def run_voice(
        self,
        audio_bytes: bytes,
        filename: str,
        conversation_id: str | None = None,
    ) -> dict[str, Any]:
        """Transcribe uploaded audio and run it through the agent.

        The uploaded bytes are written to a temporary file so the
        existing `VoicePipeline.run` (which operates on a `Path`) can
        be reused without modification.

        Args:
            audio_bytes: The raw uploaded audio file contents.
            filename: The original uploaded filename, used to preserve
                the file extension.
            conversation_id: Optional existing conversation identifier.

        Returns:
            dict[str, Any]: A mapping with `transcript`, `answer`,
                `citations`, `evaluation`, `conversation_id`, and
                `request_id`, ready to construct a `VoiceResponse`.
        """
        suffix = Path(filename).suffix or ".wav"

        with tempfile.NamedTemporaryFile(suffix=suffix) as temp_file:
            temp_file.write(audio_bytes)
            temp_file.flush()
            result = self._pipeline.run(
                Path(temp_file.name), conversation_id=conversation_id
            )

        logger.info(
            "voice_service_completed",
            request_id=result.request_id,
            conversation_id=result.conversation_id,
        )

        return {
            "transcript": result.transcript,
            "answer": result.answer,
            "citations": result.citations,
            "evaluation": result.evaluation,
            "conversation_id": result.conversation_id,
            "request_id": result.request_id,
        }