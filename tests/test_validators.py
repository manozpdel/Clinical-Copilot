"""Tests for request payload validation utilities."""

from security.validators import (
    is_valid_json_content_type,
    is_valid_multipart_content_type,
    is_within_size_limit,
    sanitize_text,
)


def test_is_valid_json_content_type_accepts_json() -> None:
    """A standard JSON content type should be accepted."""
    assert is_valid_json_content_type("application/json") is True


def test_is_valid_json_content_type_rejects_other_types() -> None:
    """A non-JSON content type should be rejected."""
    assert is_valid_json_content_type("text/plain") is False


def test_is_valid_json_content_type_rejects_none() -> None:
    """A missing content type should be rejected."""
    assert is_valid_json_content_type(None) is False


def test_is_valid_multipart_content_type_accepts_multipart() -> None:
    """A multipart content type (with boundary) should be accepted."""
    assert is_valid_multipart_content_type("multipart/form-data; boundary=xyz") is True


def test_sanitize_text_removes_control_characters() -> None:
    """Control characters should be stripped, but newlines/tabs preserved."""
    dirty = "hello\x00world\x1f!\nnext line\tindented"

    clean = sanitize_text(dirty)

    assert "\x00" not in clean
    assert "\x1f" not in clean
    assert "\n" in clean
    assert "\t" in clean


def test_is_within_size_limit_true_when_under() -> None:
    """A payload under the limit should pass."""
    assert is_within_size_limit(100, 1000) is True


def test_is_within_size_limit_false_when_over() -> None:
    """A payload over the limit should fail."""
    assert is_within_size_limit(2000, 1000) is False
