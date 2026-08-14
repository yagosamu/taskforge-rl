"""Batch collection helper."""


def collect_batches(items: list[object], size: int) -> list[list[object]]:
    """Split items into batches."""
    batches: list[list[object]] = []
    for index in range(0, len(items), size):
        batches.append(items[index:index + size])
    return batches
