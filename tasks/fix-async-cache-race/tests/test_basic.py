"""Visible async cache tests."""

import asyncio

from cache import AsyncCache


def test_sequential_cache_hit() -> None:
    """Sequential calls reuse cached values."""
    calls = 0
    cache = AsyncCache()

    async def loader() -> str:
        nonlocal calls
        calls += 1
        return "value"

    async def scenario() -> None:
        assert await cache.get("a", loader) == "value"
        assert await cache.get("a", loader) == "value"

    asyncio.run(scenario())
    assert calls == 1
