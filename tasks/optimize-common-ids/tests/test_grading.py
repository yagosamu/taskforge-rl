"""Hidden matcher performance tests."""

import time

from matcher import common_ids


def test_large_inputs_are_fast() -> None:
    """Large inputs should avoid quadratic membership checks."""
    left = list(range(20_000))
    right = list(range(10_000, 30_000))
    started = time.perf_counter()
    result = common_ids(left, right)
    elapsed = time.perf_counter() - started
    assert result[:3] == [10_000, 10_001, 10_002]
    assert len(result) == 10_000
    assert elapsed < 0.2
