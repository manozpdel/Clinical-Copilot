"""Request payload validation utilities.

This module is responsible ONLY for pure validation/sanitization
functions. It contains no middleware, routing, or persistence logic.
"""

import re

_CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

_ALLOWED_JSON_CONTENT_TYPES = ("application/json",)
_ALLOWED_MULTIPART_CONTENT_TYPES = ("multipart/form-data",)


def is_valid_content_type(
    content_type: str | None, allowed_prefixes: tuple[str, ...]
) -> bool:
    """Check whether a request's Content-Type header is acceptable.

    Args:
        content_type: The raw `Content-Type` header value, or None.
        allowed_prefixes: Content-type prefixes considered valid.

    Returns:
        bool: True if `content_type` starts with one of
            `allowed_prefixes`.
    """
    if not content_type:
        return False
    return any(content_type.lower().startswith(prefix) for prefix in allowed_prefixes)


def is_valid_json_content_type(content_type: str | None) -> bool:
    """Check whether a request's Content-Type header indicates JSON.

    Args:
        content_type: The raw `Content-Type` header value, or None.

    Returns:
        bool: True if the content type indicates a JSON payload.
    """
    return is_valid_content_type(content_type, _ALLOWED_JSON_CONTENT_TYPES)


def is_valid_multipart_content_type(content_type: str | None) -> bool:
    """Check whether a request's Content-Type header indicates multipart form data.

    Args:
        content_type: The raw `Content-Type` header value, or None.

    Returns:
        bool: True if the content type indicates a multipart form
            payload.
    """
    return is_valid_content_type(content_type, _ALLOWED_MULTIPART_CONTENT_TYPES)


def sanitize_text(value: str) -> str:
    """Strip non-printable control characters from user-supplied text.

    Args:
        value: The raw text to sanitize.

    Returns:
        str: The text with control characters (other than newline and
            tab) removed.
    """
    return _CONTROL_CHAR_PATTERN.sub("", value)


def is_within_size_limit(byte_length: int, max_bytes: int) -> bool:
    """Check whether a payload's byte length is within an allowed limit.

    Args:
        byte_length: The size of the payload, in bytes.
        max_bytes: The maximum allowed size, in bytes.

    Returns:
        bool: True if `byte_length` does not exceed `max_bytes`.
    """
    return byte_length <= max_bytes
