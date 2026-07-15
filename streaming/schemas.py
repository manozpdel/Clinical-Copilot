"""Pydantic schemas for the real-time streaming layer.

This module is responsible ONLY for defining the shape of a stream
event. It contains no event-construction, serialization, or transport
logic.
"""

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

EventType = Literal[
    "token",
    "node_start",
    "node_complete",
    "tool_start",
    "tool_complete",
    "citation",
    "evaluation",
    "progress",
    "heartbeat",
    "finished",
    "error",
]


class StreamEvent(BaseModel):
    """A single event emitted during a streamed agent execution.

    Attributes:
        event: The event type.
        data: Event-specific payload.
        timestamp: UTC timestamp the event was created.
    """

    event: EventType
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
