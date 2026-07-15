"""CLI entry point demonstrating the /stream/query SSE endpoint via httpx."""

import httpx

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger


def main() -> None:
    """Prompt for a question and a bearer token, then print streamed events."""
    configure_logging()
    logger = get_logger(__name__)
    settings = get_settings()

    print("Enter your question")
    question = input("> ").strip()
    if not question:
        print("No question entered. Exiting.")
        return

    print("Enter your access token (from /auth/login or /auth/register)")
    token = input("> ").strip()

    base_url = f"http://{settings.host}:{settings.port}"
    params = {"question": question, "token": token}

    with httpx.Client(timeout=None) as client:
        with client.stream("GET", f"{base_url}/stream/query", params=params) as response:
            if response.status_code != 200:
                print(f"Request failed with status {response.status_code}.")
                return

            for line in response.iter_lines():
                if line:
                    print(line)

    logger.info("stream_demo_finished")


if __name__ == "__main__":
    main()
