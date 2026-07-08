"""Tests for the speech-to-text transcriber wrapper."""

import pytest

from voice.transcriber import Transcriber, TranscriptionError
from voice.models import TranscriptionResult


class _FlakyTranscriber(Transcriber):
    """A fake transcriber that fails a configurable number of times."""

    def __init__(self, fail_times: int) -> None:
        """Initialize the fake transcriber.

        Args:
            fail_times: Number of times `transcribe` should raise
                before succeeding.
        """
        self._fail_times = fail_times
        self._calls = 0

    def transcribe(self, audio_bytes: bytes, filename: str) -> TranscriptionResult:
        """Raise for the first `fail_times` calls, then succeed.

        Args:
            audio_bytes: The raw audio file contents (unused).
            filename: Original filename (unused).

        Returns:
            TranscriptionResult: A canned successful result once the
                failure budget is exhausted.

        Raises:
            RuntimeError: While the failure budget remains.
        """
        self._calls += 1
        if self._calls <= self._fail_times:
            raise RuntimeError("transient provider error")
        return TranscriptionResult(
            text="What medications is patient_001 taking?",
            provider="fake",
            model="fake-model",
        )


def test_transcriber_interface_returns_structured_result() -> None:
    """A successful transcriber call should return a structured result."""
    transcriber = _FlakyTranscriber(fail_times=0)

    result = transcriber.transcribe(b"audio bytes", "clip.wav")

    assert result.text == "What medications is patient_001 taking?"
    assert result.provider == "fake"
    assert result.model == "fake-model"


class _AlwaysFailingTranscriber(Transcriber):
    """A fake transcriber that always raises TranscriptionError."""

    def transcribe(self, audio_bytes: bytes, filename: str) -> TranscriptionResult:
        """Always raise a TranscriptionError.

        Args:
            audio_bytes: The raw audio file contents (unused).
            filename: Original filename (unused).

        Raises:
            TranscriptionError: Always.
        """
        raise TranscriptionError("provider permanently unavailable")


def test_transcriber_raises_transcription_error_on_permanent_failure() -> None:
    """A permanently failing transcriber should raise TranscriptionError."""
    transcriber = _AlwaysFailingTranscriber()

    with pytest.raises(TranscriptionError):
        transcriber.transcribe(b"audio bytes", "clip.wav")