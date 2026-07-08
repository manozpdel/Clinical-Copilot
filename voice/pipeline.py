"""Voice pipeline orchestration for Clinical Copilot.

This module is responsible ONLY for connecting audio validation,
transcription, conversation memory, and the existing LangGraph agent
(Parts 5/6) into a single voice-turn workflow. It contains no audio
decoding, transcription-provider, memory-storage, or graph-construction
logic of its own; all of that is reused from `voice.audio`,
`voice.transcriber`, `voice.memory`/`voice.session`, and `agent.graph`.
"""

import uuid
from pathlib import Path
from typing import Any

from langgraph.graph.state import CompiledStateGraph

from app.core.config import Settings
from app.core.logging import get_logger
from agent.state import create_empty_state
from voice.audio import validate_audio_file
from voice.models import VoiceChatResult
from voice.session import SessionManager
from voice.transcriber import Transcriber, transcribe_file

logger = get_logger(__name__)


class VoicePipeline:
    """Orchestrates the Audio -> Transcriber -> Memory -> Agent -> Response flow."""

    def __init__(
        self,
        settings: Settings,
        transcriber: Transcriber,
        graph: CompiledStateGraph,
        session_manager: SessionManager | None = None,
    ) -> None:
        """Initialize the voice pipeline.

        Args:
            settings: Active application settings.
            transcriber: Transcriber implementation used to convert
                audio to text.
            graph: The compiled LangGraph agent graph, reused unchanged
                from Parts 5/6.
            session_manager: Optional session manager override. A new
                instance is created when not provided.
        """
        self._settings = settings
        self._transcriber = transcriber
        self._graph = graph
        self._sessions = session_manager or SessionManager(
            max_history=settings.max_conversation_history
        )

    def run(
        self, audio_path: Path, conversation_id: str | None = None
    ) -> VoiceChatResult:
        """Run one full voice turn: transcribe audio and query the agent.

        Args:
            audio_path: Path to the audio file to transcribe.
            conversation_id: Optional existing conversation session
                identifier. A new session is created when not provided.

        Returns:
            VoiceChatResult: The transcript, agent answer, citations,
                evaluation, and updated conversation history.

        Raises:
            voice.audio.AudioValidationError: If the audio file fails
                validation.
            voice.transcriber.TranscriptionError: If transcription
                fails after all retries.
        """
        session_id = conversation_id or self._sessions.create_session()
        memory = self._sessions.get_memory(session_id)

        audio_bytes = validate_audio_file(
            audio_path, self._settings.supported_audio_formats
        )
        transcription = transcribe_file(audio_path, self._transcriber, audio_bytes)
        logger.info("voice_transcription_complete", conversation_id=session_id)

        if self._settings.enable_memory:
            memory.append("user", transcription.text)

        initial_state = create_empty_state()
        initial_state["question"] = transcription.text
        initial_state["conversation_id"] = session_id
        initial_state["request_id"] = uuid.uuid4().hex

        final_state: dict[str, Any] = dict(initial_state)
        for step in self._graph.stream(initial_state):
            for _node_name, node_update in step.items():
                final_state.update(node_update)

        answer = final_state.get("answer", "")

        if self._settings.enable_memory:
            memory.append("assistant", answer)

        logger.info("voice_pipeline_turn_complete", conversation_id=session_id)

        return VoiceChatResult(
            transcript=transcription.text,
            answer=answer,
            citations=final_state.get("citations", []),
            evaluation=final_state.get("evaluation", {}),
            conversation_id=session_id,
            request_id=final_state.get("request_id", ""),
            history=memory.history(),
            metadata=final_state.get("metadata", {}),
        )