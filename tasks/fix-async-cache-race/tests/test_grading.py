"""Hidden async cache tests."""

import asyncio

from cache import AsyncCache


def test_concurrent_calls_share_one_loader() -> None:
    """Concurrent calls for one key share the in-flight load."""
    calls = 0
    cache = AsyncCache()

    async def loader() -> str:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.01)
        return "value"

    async def scenario() -> list[str]:
        return await asyncio.gather(cache.get("a", loader), cache.get("a", loader))

    assert asyncio.run(scenario()) == ["value", "value"]
    assert calls == 1
