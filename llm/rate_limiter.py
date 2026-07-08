"""A simple thread-safe, sliding-window client-side rate limiter.

This module is responsible ONLY for proactively throttling outgoing
requests to stay within a configured rate. It contains no HTTP,
retry, or provider-specific error-handling logic.
"""

import threading
import time
from collections import deque


class RateLimiter:
    """Throttles callers to at most `max_requests` per `period_seconds`.

    Uses a sliding time window: each call to `acquire` blocks only long
    enough to ensure no more than `max_requests` calls have started
    within the trailing `period_seconds` window.
    """

    def __init__(self, max_requests: int, period_seconds: float) -> None:
        """Initialize the rate limiter.

        Args:
            max_requests: Maximum number of requests allowed within any
                trailing window of `period_seconds`.
            period_seconds: Length of the sliding time window, in
                seconds.
        """
        self._max_requests = max_requests
        self._period_seconds = period_seconds
        self._request_timestamps: deque[float] = deque()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        """Block, if necessary, until a new request is permitted.

        Records the timestamp of the permitted request before
        returning, so subsequent calls correctly account for it within
        the sliding window.
        """
        while True:
            with self._lock:
                now = time.monotonic()
                window_start = now - self._period_seconds

                while (
                    self._request_timestamps
                    and self._request_timestamps[0] < window_start
                ):
                    self._request_timestamps.popleft()

                if len(self._request_timestamps) < self._max_requests:
                    self._request_timestamps.append(now)
                    return

                oldest = self._request_timestamps[0]
                wait_time = oldest + self._period_seconds - now

            time.sleep(max(wait_time, 0.0))