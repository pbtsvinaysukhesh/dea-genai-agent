"""
Shared Retry & Circuit-Breaker Utilities
=========================================
Provides a reusable ``@retry_with_backoff`` decorator and a lightweight
``CircuitBreaker`` class so every network/API call uses the same resilient
pattern instead of hand-rolled retry loops.

Usage:
    from src.retry import retry_with_backoff, CircuitBreaker

    @retry_with_backoff(max_retries=3, backoff_factor=2.0, exceptions=(requests.RequestException,))
    def call_api():
        ...

    breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
    with breaker:
        call_api()
"""

import time
import logging
import functools
from typing import Tuple, Type, Optional, Callable
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


# ── Retry Decorator ──────────────────────────────────────────────────────────

def retry_with_backoff(
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    initial_delay: float = 1.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable] = None,
):
    """
    Decorator that retries a function with exponential backoff.

    Args:
        max_retries:    Maximum number of retry attempts.
        backoff_factor: Multiplier applied to the delay after each retry.
        initial_delay:  Seconds to wait before the first retry.
        exceptions:     Tuple of exception types that trigger a retry.
        on_retry:       Optional callback ``fn(attempt, exception, delay)``
                        invoked before each retry sleep.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exception = exc
                    if attempt == max_retries:
                        logger.error(
                            f"[Retry] {func.__name__} failed after "
                            f"{max_retries + 1} attempts: {exc}"
                        )
                        raise

                    if on_retry:
                        on_retry(attempt + 1, exc, delay)

                    logger.warning(
                        f"[Retry] {func.__name__} attempt {attempt + 1}/{max_retries + 1} "
                        f"failed: {exc}. Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                    delay *= backoff_factor

            raise last_exception  # type: ignore[misc]

        return wrapper
    return decorator


# ── Async Retry Decorator ────────────────────────────────────────────────────

def async_retry_with_backoff(
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    initial_delay: float = 1.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
):
    """Async version of retry_with_backoff for ``async def`` functions."""
    import asyncio

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:
                    last_exception = exc
                    if attempt == max_retries:
                        logger.error(
                            f"[AsyncRetry] {func.__name__} failed after "
                            f"{max_retries + 1} attempts: {exc}"
                        )
                        raise

                    logger.warning(
                        f"[AsyncRetry] {func.__name__} attempt {attempt + 1}/{max_retries + 1} "
                        f"failed: {exc}. Retrying in {delay:.1f}s..."
                    )
                    await asyncio.sleep(delay)
                    delay *= backoff_factor

            raise last_exception  # type: ignore[misc]

        return wrapper
    return decorator


# ── Circuit Breaker ──────────────────────────────────────────────────────────

class CircuitBreaker:
    """
    Lightweight circuit breaker.

    States:
        CLOSED   → normal operation; failures are counted.
        OPEN     → all calls are short-circuited (raise immediately).
        HALF_OPEN → one probe call is allowed; success resets, failure re-opens.

    Usage:
        breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)

        if breaker.can_execute():
            try:
                result = call_api()
                breaker.record_success()
            except Exception as e:
                breaker.record_failure()
                raise
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        name: str = "default",
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = timedelta(seconds=recovery_timeout)
        self.name = name

        self._state = self.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._success_count = 0

    @property
    def state(self) -> str:
        if self._state == self.OPEN and self._last_failure_time:
            if datetime.now() - self._last_failure_time >= self.recovery_timeout:
                self._state = self.HALF_OPEN
                logger.info(f"[CircuitBreaker:{self.name}] → HALF_OPEN (recovery window elapsed)")
        return self._state

    def can_execute(self) -> bool:
        """Check whether a call is allowed."""
        current = self.state
        if current == self.CLOSED:
            return True
        if current == self.HALF_OPEN:
            return True   # one probe allowed
        # OPEN
        return False

    def record_success(self):
        """Record a successful call (resets failure counter)."""
        self._failure_count = 0
        self._success_count += 1
        if self._state == self.HALF_OPEN:
            self._state = self.CLOSED
            logger.info(f"[CircuitBreaker:{self.name}] → CLOSED (probe succeeded)")

    def record_failure(self):
        """Record a failed call."""
        self._failure_count += 1
        self._last_failure_time = datetime.now()

        if self._failure_count >= self.failure_threshold:
            self._state = self.OPEN
            logger.warning(
                f"[CircuitBreaker:{self.name}] → OPEN "
                f"(failures={self._failure_count}, threshold={self.failure_threshold})"
            )

    def get_stats(self) -> dict:
        return {
            "name": self.name,
            "state": self.state,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout_s": self.recovery_timeout.total_seconds(),
        }


__all__ = [
    "retry_with_backoff",
    "async_retry_with_backoff",
    "CircuitBreaker",
]
