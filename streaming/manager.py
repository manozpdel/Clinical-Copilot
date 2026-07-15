"""WebSocket connection management.

This module is responsible ONLY for tracking active WebSocket
connections and sending events to them. It contains no authentication,
event-construction, or pipeline-orchestration logic.
"""

import uuid

from fastapi import WebSocket

from app.core.logging import get_logger
from streaming.schemas import StreamEvent
from streaming.serializers import to_json

logger = get_logger(__name__)


class ConnectionManager:
    """Tracks active WebSocket connections, keyed by a generated connection ID."""

    def __init__(self) -> None:
        """Initialize an empty connection registry."""
        self._connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket) -> str:
        """Accept a WebSocket connection and register it.

        Args:
            websocket: The WebSocket connection to accept.

        Returns:
            str: A generated connection ID for this connection.
        """
        await websocket.accept()
        connection_id = uuid.uuid4().hex
        self._connections[connection_id] = websocket
        logger.info("ws_connected", connection_id=connection_id)
        return connection_id

    def disconnect(self, connection_id: str) -> None:
        """Remove a connection from the registry.

        Args:
            connection_id: Identifier of the connection to remove.
        """
        self._connections.pop(connection_id, None)
        logger.info("ws_disconnected", connection_id=connection_id)

    async def send_event(self, connection_id: str, event: StreamEvent) -> None:
        """Send a single event to a specific connection, if still open.

        Args:
            connection_id: Identifier of the target connection.
            event: The event to send.
        """
        websocket = self._connections.get(connection_id)
        if websocket is not None:
            await websocket.send_text(to_json(event))

    def active_connection_count(self) -> int:
        """Return the number of currently tracked connections.

        Returns:
            int: The active connection count.
        """
        return len(self._connections)
