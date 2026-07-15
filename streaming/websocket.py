"""WebSocket transport for the streaming agent pipeline.

This module is responsible ONLY for the `GET /ws` WebSocket route and
its connection lifecycle (accept, receive, send, disconnect). It
contains no pipeline orchestration logic (see `streaming.service`).
"""

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from auth.dependencies import get_current_user_ws
from database.dependencies import get_db
from database.models import User
from streaming.events import error_event
from streaming.manager import ConnectionManager
from streaming.serializers import to_json
from streaming.service import StreamingService, build_streaming_service

logger = get_logger(__name__)

router = APIRouter(tags=["streaming"])

_streaming_service_singleton: StreamingService | None = None
connection_manager = ConnectionManager()


def get_streaming_service(settings: Settings = Depends(get_settings)) -> StreamingService:
    """Provide a lazily-constructed, process-wide StreamingService instance.

    Args:
        settings: Active application settings.

    Returns:
        StreamingService: The shared streaming service instance.
    """
    global _streaming_service_singleton
    if _streaming_service_singleton is None:
        _streaming_service_singleton = build_streaming_service(settings)
    return _streaming_service_singleton


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    current_user: User = Depends(get_current_user_ws),
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
    service: StreamingService = Depends(get_streaming_service),
) -> None:
    """Handle a bidirectional WebSocket connection for streamed queries.

    Each received text message is expected to be a JSON object of the
    form `{"question": "...", "conversation_id": "..."}` (the latter
    optional). The full event stream for that question is sent back
    over the same connection before waiting for the next message, so a
    single connection can be reused across multiple turns.

    Args:
        websocket: The incoming WebSocket connection.
        current_user: The authenticated user, resolved from the
            `?token=` query parameter.
        settings: Active application settings.
        db: Request-scoped async database session.
        service: The streaming service.
    """
    if not settings.enable_websockets:
        await websocket.close(code=4404, reason="WebSockets are disabled.")
        return

    connection_id = await connection_manager.connect(websocket)

    try:
        while True:
            payload = await websocket.receive_json()
            question = payload.get("question", "")
            conversation_id = payload.get("conversation_id")

            if not question.strip():
                await websocket.send_text(
                    to_json(error_event("question must not be empty."))
                )
                continue

            async for event in service.stream_query(
                question, conversation_id, current_user.id, db
            ):
                await websocket.send_text(to_json(event))

    except WebSocketDisconnect:
        logger.info("ws_client_disconnected", connection_id=connection_id)
    finally:
        connection_manager.disconnect(connection_id)
