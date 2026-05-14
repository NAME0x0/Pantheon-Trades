"""Retry helpers wrapping tenacity for the Boule hot path."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TypeVar

from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

T = TypeVar("T")


async def retry_async(
    fn: Callable[[], Awaitable[T]],
    *,
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 8.0,
    retryable: tuple[type[BaseException], ...] = (Exception,),
) -> T:
    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(retryable),
        reraise=True,
    ):
        with attempt:
            return await fn()
    raise RuntimeError("unreachable")
