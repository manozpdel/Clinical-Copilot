"""Stream event construction.

This module is responsible ONLY for building `StreamEvent` instances
for each event type. It contains no transport (SSE/WebSocket),
progress-tracking, or orchestration logic.
"""

from typing import Any

from streaming.schemas import StreamEvent


def token_event(content: str, index: int) -> StreamEvent:
    """Build a `token` event for one incremental chunk of generated text."""
    return StreamEvent(event="token", data={"content": content, "index": index})


def node_start_event(node: str) -> StreamEvent:
    """Build a `node_start` event for a LangGraph pipeline stage beginning."""
    return StreamEvent(event="node_start", data={"node": node})


def node_complete_event(node: str, duration_seconds: float) -> StreamEvent:
    """Build a `node_complete` event for a finished pipeline stage."""
    return StreamEvent(
        event="node_complete",
        data={"node": node, "duration_seconds": round(duration_seconds, 4)},
    )


def tool_start_event(tool_name: str, patient_id: str | None) -> StreamEvent:
    """Build a `tool_start` event for a mock clinical tool beginning execution."""
    return StreamEvent(event="tool_start", data={"tool": tool_name, "patient_id": patient_id})


def tool_complete_event(tool_name: str, success: bool, duration_seconds: float) -> StreamEvent:
    """Build a `tool_complete` event for a finished tool execution."""
    return StreamEvent(
        event="tool_complete",
        data={
            "tool": tool_name,
            "success": success,
            "duration_seconds": round(duration_seconds, 4),
        },
    )


def citation_event(
    patient_id: str, chunk_id: str, source_file: str, similarity: float, citation: str
) -> StreamEvent:
    """Build a `citation` event for a single retrieved/tool-derived source."""
    return StreamEvent(
        event="citation",
        data={
            "patient_id": patient_id,
            "chunk_id": chunk_id,
            "source_file": source_file,
            "similarity": similarity,
            "citation": citation,
        },
    )


def evaluation_event(message: str, scores: dict[str, Any] | None = None) -> StreamEvent:
    """Build an `evaluation` event for evaluation progress or final scores."""
    data: dict[str, Any] = {"message": message}
    if scores is not None:
        data["scores"] = scores
    return StreamEvent(event="evaluation", data=data)


def progress_event(stage: str, percent: float) -> StreamEvent:
    """Build a `progress` event reporting overall pipeline completion."""
    return StreamEvent(event="progress", data={"stage": stage, "percent": percent})


def heartbeat_event() -> StreamEvent:
    """Build a `heartbeat` event, sent during periods of no other activity."""
    return StreamEvent(event="heartbeat", data={})


def finished_event(result: dict[str, Any]) -> StreamEvent:
    """Build the terminal `finished` event carrying the full result."""
    return StreamEvent(event="finished", data=result)


def error_event(detail: str) -> StreamEvent:
    """Build an `error` event for an unrecoverable failure during streaming."""
    return StreamEvent(event="error", data={"detail": detail})
