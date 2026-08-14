"""Async caching helper."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


class AsyncCache:
    """Cache async loader results by key."""

    def __init__(self) -> None:
        """Create an empty cache."""
        self._values: dict[str, object] = {}

    async def get(self, key: str, loader: Callable[[], Awaitable[T]]) -> T:
        """Return cached value for key, loading it when needed."""
        if key not in self._values:
            self._values[key] = await loader()
        return self._values[key]  # type: ignore[return-value]
