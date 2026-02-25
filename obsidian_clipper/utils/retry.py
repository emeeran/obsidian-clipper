"""Retry utility functions."""

from __future__ import annotations

import logging
import time
from collections import deque
from collections.abc import Callable
from typing import TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitBreaker:
    """Circuit breaker to prevent cascading failures.

    Tracks recent failures and prevents attempts when threshold is exceeded.

    Example:
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)

        if cb.should_attempt():
            try:
                result = risky_operation()
                cb.record_success()
            except Exception:
                cb.record_failure()
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        """Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before circuit opens.
            recovery_timeout: Seconds to wait before allowing retry.
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._failure_times: deque[float] = deque(maxlen=failure_threshold)
        self._last_failure_time: float = 0.0

    def should_attempt(self) -> bool:
        """Check if an attempt should be made.

        Returns:
            True if circuit is closed or recovery timeout has passed.
        """
        if len(self._failure_times) < self.failure_threshold:
            return True

        # Check if recovery timeout has passed
        elapsed = time.time() - self._last_failure_time
        if elapsed >= self.recovery_timeout:
            self._failure_times.clear()
            return True

        return False

    def record_failure(self) -> None:
        """Record a failure event."""
        self._failure_times.append(time.time())
        self._last_failure_time = time.time()

    def record_success(self) -> None:
        """Record a success event, clearing failure history."""
        self._failure_times.clear()


def retry_with_backoff(
    func: Callable[[], T | None],
    max_attempts: int = 3,
    delay: float = 0.1,
    backoff: float = 1.0,
    circuit_breaker: CircuitBreaker | None = None,
    should_retry: Callable[[T | None], bool] | None = None,
) -> T | None:
    """Execute a function with retry and optional backoff.

    Args:
        func: Function to execute.
        max_attempts: Maximum number of attempts.
        delay: Initial delay between retries in seconds.
        backoff: Multiplier for delay after each attempt.
        circuit_breaker: Optional circuit breaker to prevent cascading failures.
        should_retry: Optional function to determine if retry is needed.
                      If None, retries when result is None or falsy.

    Returns:
        Result of func if successful, None otherwise.

    Example:
        def get_data():
            return fetch_from_server()

        result = retry_with_backoff(
            get_data,
            max_attempts=5,
            delay=0.1,
            should_retry=lambda x: x is None
        )
    """
    # Check circuit breaker before attempting
    if circuit_breaker and not circuit_breaker.should_attempt():
        logger.debug("Circuit breaker is open, skipping attempt")
        return None

    current_delay = delay

    for attempt in range(max_attempts):
        try:
            result = func()

            # Check if we should retry based on result
            needs_retry = (
                should_retry is not None and should_retry(result)
            ) or (should_retry is None and not result)

            if needs_retry and attempt < max_attempts - 1:
                logger.debug(
                    "Retry attempt %d/%d after %.2fs",
                    attempt + 1,
                    max_attempts,
                    current_delay,
                )
                time.sleep(current_delay)
                current_delay *= backoff
                continue

            # Record success if we got a valid result
            if circuit_breaker and result:
                circuit_breaker.record_success()

            return result

        except Exception as e:
            if attempt < max_attempts - 1:
                logger.debug(
                    "Retry attempt %d/%d after error: %s",
                    attempt + 1,
                    max_attempts,
                    e,
                )
                time.sleep(current_delay)
                current_delay *= backoff
            else:
                # Record failure on final attempt
                if circuit_breaker:
                    circuit_breaker.record_failure()
                logger.warning("All %d retry attempts failed", max_attempts)
                raise

    return None
