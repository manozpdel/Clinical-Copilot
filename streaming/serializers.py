"""Stream event serialization.

This module is responsible ONLY for converting a `StreamEvent` into
the wire formats used by SSE and WebSocket transports. It contains no
event-construction or transport-connection logic.
"""

from streaming.schemas import StreamEvent


def to_sse(event: StreamEvent) -> str:
    """Serialize a stream event into Server-Sent Events wire format.

    Args:
        event: The event to serialize.

    Returns:
        str: A complete SSE message, including the trailing blank line
            required to terminate it.
    """
    payload = event.model_dump_json()
    return f"event: {event.event}\ndata: {payload}\n\n"


def to_json(event: StreamEvent) -> str:
    """Serialize a stream event into a single JSON string for WebSocket use.

    Args:
        event: The event to serialize.

    Returns:
        str: The event encoded as a JSON object.
    """
    return event.model_dump_json()
