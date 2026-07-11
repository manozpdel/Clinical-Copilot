"""Speech-to-text transcription for the voice interaction layer.

This module is responsible ONLY for converting audio bytes into text
via a transcription provider. It contains no audio validation, memory,
session, or pipeline orchestration logic. The abstract `Transcriber`
interface keeps the provider swappable; `GroqWhisperTranscriber` is the
current implementation, backed by Groq's hosted Whisper API.
Transcription latency is recorded via `observability.metrics` and
traced via `observability.tracing`, without altering behavior.
"""

import random
import time
from abc import ABC, abstractmethod
from pathlib import Path

from groq import Groq

from app.core.config import Settings
from app.core.logging import get_logger
from observability.metrics import record_voice_transcription_latency
from observability.tracing import trace_span
from voice.models import TranscriptionResult

logger = get_logger(__name__)


class TranscriptionError(Exception):
    """Raised when audio transcription fails after all retries."""


class Transcriber(ABC):
    """Abstract interface for a speech-to-text provider."""

    @abstractmethod
    def transcribe(self, audio_bytes: bytes, filename: str) -> TranscriptionResult:
        """Transcribe raw audio bytes into text.

        Args:
            audio_bytes: The raw audio file contents.
            filename: Original filename, used to signal format to the
                provider.

        Returns:
            TranscriptionResult: The structured transcription result.

        Raises:
            TranscriptionError: If transcription fails after all
                configured retries.
        """
        raise NotImplementedError


class GroqWhisperTranscriber(Transcriber):
    """A Transcriber implementation backed by Groq's hosted Whisper API."""

    def __init__(self, settings: Settings) -> None:
        """Initialize the Groq Whisper transcriber from application settings.

        Args:
            settings: Application settings providing the API key, model
                name, timeout, and retry configuration. Uses
                `transcription_api_key` when set, otherwise falls back
                to `generation_api_key`.
        """
        self._settings = settings
        self._model = settings.groq_whisper_model
        api_key = settings.transcription_api_key or settings.generation_api_key
        self._client = Groq(api_key=api_key, timeout=settings.llm_timeout)

    def _compute_backoff_delay(self, attempt: int) -> float:
        """Compute the exponential backoff delay for a retry attempt.

        Args:
            attempt: 0-indexed count of retries already performed.

        Returns:
            float: Delay in seconds, capped at the configured maximum.
        """
        base_delay = self._settings.llm_retry_base_delay * (2**attempt)
        jitter = random.uniform(0, base_delay * 0.1)
        return min(base_delay + jitter, self._settings.llm_retry_max_delay)

    def transcribe(self, audio_bytes: bytes, filename: str) -> TranscriptionResult:
        """Transcribe audio bytes using the Groq Whisper API.

        Retries transient failures with exponential backoff up to the
        configured maximum retries.

        Args:
            audio_bytes: The raw audio file contents.
            filename: Original filename, used to signal format to the
                Groq API.

        Returns:
            TranscriptionResult: The structured transcription result.

        Raises:
            TranscriptionError: If transcription still fails after
                exhausting all configured retries.
        """
        max_attempts = self._settings.llm_max_retries + 1
        last_error: Exception | None = None

        for attempt in range(max_attempts):
            try:
                logger.info(
                    "transcription_started", model=self._model, attempt=attempt
                )
                call_start = time.monotonic()
                with trace_span("voice.transcribe", model=self._model, attempt=attempt):
                    response = self._client.audio.transcriptions.create(
                        file=(filename, audio_bytes),
                        model=self._model,
                        response_format="verbose_json",
                    )
                record_voice_transcription_latency(time.monotonic() - call_start)
                logger.info("transcription_completed", model=self._model)
                return TranscriptionResult(
                    text=response.text.strip(),
                    language=getattr(response, "language", None),
                    duration_seconds=getattr(response, "duration", None),
                    provider="groq",
                    model=self._model,
                )
            except Exception as error:  # noqa: BLE001
                last_error = error
                if attempt == max_attempts - 1:
                    break
                delay = self._compute_backoff_delay(attempt)
                logger.warning(
                    "transcription_retrying",
                    model=self._model,
                    attempt=attempt,
                    delay_seconds=round(delay, 2),
                    error=str(error),
                )
                time.sleep(delay)

        logger.error(
            "transcription_failed", model=self._model, attempts=max_attempts
        )
        raise TranscriptionError(
            f"Transcription failed after {max_attempts} attempt(s)."
        ) from last_error


def transcribe_file(
    path: Path, transcriber: Transcriber, audio_bytes: bytes
) -> TranscriptionResult:
    """Transcribe an already-validated audio file.

    Args:
        path: Path to the audio file, used only for its filename.
        transcriber: The transcriber implementation to use.
        audio_bytes: The raw, pre-validated audio file contents.

    Returns:
        TranscriptionResult: The structured transcription result.
    """
    return transcriber.transcribe(audio_bytes, filename=path.name)
