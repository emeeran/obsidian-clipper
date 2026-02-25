"""Retry utility functions."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def retry_with_backoff(
    func: Callable[[], T | None],
    max_attempts: int = 3,
    delay: float = 0.1,
    backoff: float = 1.0,
    should_retry: Callable[[T | None], bool] | None = None,
) -> T | None:
    """Execute a function with retry and optional backoff.

    Args:
        func: Function to execute.
        max_attempts: Maximum number of attempts.
        delay: Initial delay between retries in seconds.
        backoff: Multiplier for delay after each attempt.
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
                logger.warning("All %d retry attempts failed", max_attempts)
                raise

    return None
