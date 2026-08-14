"""Batch collection helper."""

_BATCHES: list[list[object]] = []


def collect_batches(items: list[object], size: int) -> list[list[object]]:
    """Split items into batches."""
    for index in range(0, len(items), size):
        _BATCHES.append(items[index:index + size])
    return _BATCHES
