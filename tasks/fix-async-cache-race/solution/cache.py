"""Async caching helper."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


class AsyncCache:
    """Cache async loader results by key."""

    def __init__(self) -> None:
        """Create an empty cache."""
        self._values: dict[str, object] = {}
        self._inflight: dict[str, asyncio.Task[object]] = {}

    async def get(self, key: str, loader: Callable[[], Awaitable[T]]) -> T:
        """Return cached value for key, loading it when needed."""
        if key in self._values:
            return self._values[key]  # type: ignore[return-value]
        if key not in self._inflight:
            self._inflight[key] = asyncio.create_task(loader())
        try:
            value = await self._inflight[key]
        finally:
            self._inflight.pop(key, None)
        self._values[key] = value
        return value  # type: ignore[return-value]
