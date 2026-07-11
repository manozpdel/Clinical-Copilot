"""Request and correlation ID generation.

This module is responsible ONLY for generating unique request and
correlation identifiers. It contains no logging, tracing, or
middleware logic.
"""

import uuid


def generate_request_id() -> str:
    """Generate a new unique request identifier.

    Returns:
        str: A UUID4 hex string, unique to a single request.
    """
    return uuid.uuid4().hex


def generate_correlation_id() -> str:
    """Generate a new unique correlation identifier.

    A correlation ID identifies a logical unit of work that may span
    multiple requests (e.g. a multi-turn conversation), distinct from
    the per-request `request_id`.

    Returns:
        str: A UUID4 hex string.
    """
    return uuid.uuid4().hex
