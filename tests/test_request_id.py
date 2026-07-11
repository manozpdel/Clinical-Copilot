"""Tests for request/correlation ID generation."""

from observability.request_id import generate_correlation_id, generate_request_id


def test_generate_request_id_is_unique() -> None:
    """Successive calls should produce distinct request IDs."""
    first = generate_request_id()
    second = generate_request_id()

    assert first != second
    assert len(first) == 32


def test_generate_correlation_id_is_unique() -> None:
    """Successive calls should produce distinct correlation IDs."""
    first = generate_correlation_id()
    second = generate_correlation_id()

    assert first != second
    assert len(first) == 32
