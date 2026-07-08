"""CLI entry point for voice interaction with the Clinical Copilot agent."""

from pathlib import Path

from agent.graph import build_graph
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from voice.audio import AudioValidationError
from voice.pipeline import VoicePipeline
from voice.transcriber import GroqWhisperTranscriber, TranscriptionError


def main() -> None:
    """Prompt for an audio file, run the voice pipeline, and print the results."""
    configure_logging()
    logger = get_logger(__name__)
    settings = get_settings()

    graph = build_graph(settings)
    transcriber = GroqWhisperTranscriber(settings)
    pipeline = VoicePipeline(settings=settings, transcriber=transcriber, graph=graph)

    print("Enter path to audio file")
    raw_path = input("> ").strip()

    if not raw_path:
        print("No path entered. Exiting.")
        return

    audio_path = Path(raw_path)

    try:
        result = pipeline.run(audio_path)
    except AudioValidationError as error:
        print(f"\nAudio validation failed: {error}")
        return
    except TranscriptionError as error:
        print(f"\nTranscription failed: {error}")
        return

    print("\nTranscript\n")
    print(result.transcript)

    print("\nAnswer\n")
    print(result.answer)

    print("\nCitations\n")
    for citation in result.citations:
        print(citation)

    print("\nEvaluation\n")
    for key, value in result.evaluation.items():
        print(f"{key}: {value}")

    print("\nConversation History\n")
    for turn in result.history:
        print(f"[{turn.role}] {turn.content}")

    logger.info(
        "voice_chat_finished",
        conversation_id=result.conversation_id,
        request_id=result.request_id,
    )


if __name__ == "__main__":
    main()