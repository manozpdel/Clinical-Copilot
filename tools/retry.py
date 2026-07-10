"""Retry utilities for the mock clinical tools layer.

This module is responsible ONLY for retrying transient failures with a
configurable maximum attempt count and delay. It contains no tool
implementation, registration, routing, or validation logic.
"""

import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


class RetryExhaustedError(Exception):
    """Raised when a retried call still fails after all attempts."""


def retry_call[T](
    func: Callable[[], T],
    max_attempts: int,
    delay_seconds: float,
    retry_exceptions: tuple[type[Exception], ...] = (Exception,),
) -> T:
    """Call a function, retrying on specified exceptions with a fixed delay.

    Args:
        func: A zero-argument callable to invoke.
        max_attempts: Maximum number of attempts, including the first
            call. Must be at least 1.
        delay_seconds: Delay, in seconds, to wait between attempts.
        retry_exceptions: Exception types that should trigger a retry.
            Any other exception is raised immediately without retrying.

    Returns:
        T: The return value of `func` on the first successful attempt.

    Raises:
        ValueError: If `max_attempts` is less than 1.
        RetryExhaustedError: If every attempt raises a retryable
            exception.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1.")

    last_error: Exception | None = None

    for attempt in range(max_attempts):
        try:
            return func()
        except retry_exceptions as error:
            last_error = error
            if attempt < max_attempts - 1:
                time.sleep(delay_seconds)

    raise RetryExhaustedError(
        f"Call failed after {max_attempts} attempt(s)."
    ) from last_error
