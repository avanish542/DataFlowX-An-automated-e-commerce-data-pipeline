"""
A small retry decorator with exponential backoff.

This is intentionally simple - just enough to make the REST API client
resilient to transient failures, without pulling in a dependency like
tenacity for a single use case.
"""

import functools
import time
from collections.abc import Callable
from typing import TypeVar

from dataflowx.utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay_seconds: float = 1.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Retry a function on failure using exponential backoff.

    Attempt 1 fails -> wait base_delay
    Attempt 2 fails -> wait base_delay * 2
    Attempt 3 fails -> wait base_delay * 4
    ... up to max_attempts total attempts, then re-raise.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception: Exception | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exception = exc
                    if attempt == max_attempts:
                        logger.error(
                            "%s failed after %d attempts: %s",
                            func.__name__,
                            max_attempts,
                            exc,
                        )
                        raise
                    delay = base_delay_seconds * (2 ** (attempt - 1))
                    logger.warning(
                        "%s failed (attempt %d/%d): %s. Retrying in %.1fs",
                        func.__name__,
                        attempt,
                        max_attempts,
                        exc,
                        delay,
                    )
                    time.sleep(delay)
            # Unreachable, but keeps type checkers happy.
            raise last_exception  # type: ignore[misc]

        return wrapper

    return decorator
