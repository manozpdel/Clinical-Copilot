"""Tests for the retry utility."""

import pytest

from tools.retry import RetryExhaustedError, retry_call


def test_retry_call_succeeds_on_first_attempt() -> None:
    """A function that succeeds immediately should not be retried."""
    calls = {"count": 0}

    def func() -> str:
        calls["count"] += 1
        return "ok"

    result = retry_call(func, max_attempts=3, delay_seconds=0.0)

    assert result == "ok"
    assert calls["count"] == 1


def test_retry_call_succeeds_after_transient_failures() -> None:
    """A function should be retried until it succeeds within max_attempts."""
    calls = {"count": 0}

    def func() -> str:
        calls["count"] += 1
        if calls["count"] < 3:
            raise ConnectionError("transient failure")
        return "ok"

    result = retry_call(
        func,
        max_attempts=5,
        delay_seconds=0.0,
        retry_exceptions=(ConnectionError,),
    )

    assert result == "ok"
    assert calls["count"] == 3


def test_retry_call_raises_after_exhausting_attempts() -> None:
    """RetryExhaustedError should be raised once max_attempts is reached."""

    def func() -> str:
        raise ConnectionError("always fails")

    with pytest.raises(RetryExhaustedError):
        retry_call(
            func,
            max_attempts=3,
            delay_seconds=0.0,
            retry_exceptions=(ConnectionError,),
        )


def test_retry_call_does_not_retry_non_matching_exceptions() -> None:
    """An exception not in retry_exceptions should propagate immediately."""
    calls = {"count": 0}

    def func() -> str:
        calls["count"] += 1
        raise ValueError("not retryable")

    with pytest.raises(ValueError):
        retry_call(
            func,
            max_attempts=3,
            delay_seconds=0.0,
            retry_exceptions=(ConnectionError,),
        )

    assert calls["count"] == 1


def test_retry_call_rejects_invalid_max_attempts() -> None:
    """max_attempts below 1 should raise a ValueError."""
    with pytest.raises(ValueError):
        retry_call(lambda: "ok", max_attempts=0, delay_seconds=0.0)