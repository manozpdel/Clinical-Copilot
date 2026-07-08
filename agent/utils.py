"""Small, dependency-free helper utilities for the agent layer."""

import uuid


def generate_id() -> str:
    """Generate a new random unique identifier.

    Returns:
        str: A UUID4 hex string.
    """
    return uuid.uuid4().hex


def normalize_whitespace(text: str) -> str:
    """Collapse and trim whitespace in a string.

    Args:
        text: The raw text to normalize.

    Returns:
        str: The text with leading/trailing whitespace removed and
            internal whitespace runs collapsed to single spaces.
    """
    return " ".join(text.split())