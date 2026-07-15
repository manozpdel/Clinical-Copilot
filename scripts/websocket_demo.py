"""CLI entry point demonstrating the /ws WebSocket endpoint."""

import asyncio
import json

import websockets

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger


async def run_demo(question: str, token: str) -> None:
    """Connect to /ws, send one question, and print every received event.

    Args:
        question: The question to ask.
        token: A valid access token.
    """
    settings = get_settings()
    uri = f"ws://{settings.host}:{settings.port}/ws?token={token}"

    async with websockets.connect(uri) as websocket:
        await websocket.send(json.dumps({"question": question}))

        while True:
            message = await websocket.recv()
            event = json.loads(message)
            print(event)
            if event.get("event") in ("finished", "error"):
                break


def main() -> None:
    """Prompt for a question and a bearer token, then run the WebSocket demo."""
    configure_logging()
    logger = get_logger(__name__)

    print("Enter your question")
    question = input("> ").strip()
    if not question:
        print("No question entered. Exiting.")
        return

    print("Enter your access token (from /auth/login or /auth/register)")
    token = input("> ").strip()

    asyncio.run(run_demo(question, token))
    logger.info("websocket_demo_finished")


if __name__ == "__main__":
    main()
