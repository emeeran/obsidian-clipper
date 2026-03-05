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
) -> T | None:
    """Execute a function with retry and backoff.

    Args:
        func: Function to execute.
        max_attempts: Maximum number of attempts.
        delay: Initial delay between retries in seconds.
        backoff: Multiplier for delay after each attempt.

    Returns:
        Result of func if successful, None otherwise.
    """
    current_delay = delay

    for attempt in range(max_attempts):
        try:
            result = func()
            if result:
                return result
            if attempt < max_attempts - 1:
                logger.debug("Retry attempt %d/%d", attempt + 1, max_attempts)
                time.sleep(current_delay)
                current_delay *= backoff
        except Exception as e:
            if attempt < max_attempts - 1:
                logger.debug("Retry attempt %d/%d after error: %s", attempt + 1, max_attempts, e)
                time.sleep(current_delay)
                current_delay *= backoff
            else:
                logger.warning("All %d retry attempts failed", max_attempts)
                raise

    return None
