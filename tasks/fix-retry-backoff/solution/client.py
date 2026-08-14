"""Small client helpers used by the retry task."""

from __future__ import annotations

from collections.abc import Callable
from time import sleep
from typing import TypeVar

T = TypeVar("T")


def retry(func: Callable[[], T], *, attempts: int = 3, backoff_s: float = 0.0) -> T:
    """Call a function until it succeeds or attempts are exhausted."""
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            return func()
        except Exception as exc:
            last_error = exc
            if attempt < attempts - 1 and backoff_s:
                sleep(backoff_s)
    assert last_error is not None
    raise last_error
