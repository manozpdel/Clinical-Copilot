"""Tests for the /api/voice endpoint."""

from typing import Any

from fastapi.testclient import TestClient

from app.api.voice import get_voice_service
from app.main import app


class _FakeVoiceService:
    """A fake VoiceService returning a canned result without network calls."""

    def run_voice(
        self,
        audio_bytes: bytes,
        filename: str,
        conversation_id: str | None = None,
    ) -> dict[str, Any]:
        """Return a canned voice result, ignoring the actual audio content.

        Args:
            audio_bytes: The raw uploaded audio file contents (unused).
            filename: The original uploaded filename (unused).
            conversation_id: Optional existing conversation identifier.

        Returns:
            dict[str, Any]: A canned result matching VoiceResponse.
        """
        return {
            "transcript": "What medications is patient_001 taking?",
            "answer": "Patient is taking Metformin 500mg twice daily.",
            "citations": [
                "[Citation: Patient patient_001, Chunk c1, patient_001.txt]"
            ],
            "evaluation": {
                "faithfulness": 0.85,
                "citation_present": True,
                "context_used": True,
            },
            "conversation_id": conversation_id or "conv-456",
            "request_id": "req-456",
        }


def test_submit_voice_returns_transcript_and_answer() -> None:
    """A valid audio upload should return a transcript, answer, and citations."""
    app.dependency_overrides[get_voice_service] = lambda: _FakeVoiceService()
    client = TestClient(app)

    response = client.post(
        "/api/voice",
        files={"file": ("clip.wav", b"RIFF" + b"\x00" * 40, "audio/wav")},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert "medications" in body["transcript"]
    assert "Metformin" in body["answer"]
    assert len(body["citations"]) == 1
    assert body["evaluation"]["faithfulness"] == 0.85


def test_submit_voice_rejects_oversized_upload() -> None:
    """An upload exceeding max_upload_size should return a 413 error."""
    app.dependency_overrides[get_voice_service] = lambda: _FakeVoiceService()
    client = TestClient(app)

    oversized_content = b"\x00" * (11_000_000)
    response = client.post(
        "/api/voice",
        files={"file": ("clip.wav", oversized_content, "audio/wav")},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 413


def test_submit_voice_preserves_provided_conversation_id() -> None:
    """A provided conversation_id form field should be passed to the service."""
    app.dependency_overrides[get_voice_service] = lambda: _FakeVoiceService()
    client = TestClient(app)

    response = client.post(
        "/api/voice",
        files={"file": ("clip.wav", b"RIFF" + b"\x00" * 40, "audio/wav")},
        data={"conversation_id": "my-voice-convo"},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["conversation_id"] == "my-voice-convo"