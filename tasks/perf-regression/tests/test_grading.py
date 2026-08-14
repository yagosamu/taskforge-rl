import time

from lookup import common_active_ids

MAX_DURATION_S = 0.25


def test_preserves_left_order_and_deduplicates() -> None:
    left = [
        {"id": index, "active": True}
        for index in [*range(4000, 7000), *range(4000, 7000)]
    ]
    right = [{"id": index, "active": True} for index in range(8000)]
    started = time.perf_counter()

    result = common_active_ids(left, right)

    assert result[:3] == [4000, 4001, 4002]
    assert result[-1] == 6999
    assert len(result) == 3000
    assert time.perf_counter() - started < MAX_DURATION_S


def test_requires_active_on_both_sides() -> None:
    left = [{"id": index, "active": True} for index in range(6000)]
    right = [{"id": index, "active": False} for index in range(6000)]
    started = time.perf_counter()

    assert common_active_ids(left, right) == []
    assert time.perf_counter() - started < MAX_DURATION_S


def test_large_input_runtime() -> None:
    left = [{"id": index, "active": True} for index in range(6000)]
    right = [{"id": index, "active": True} for index in range(3000, 9000)]
    started = time.perf_counter()

    result = common_active_ids(left, right)

    assert result[:3] == [3000, 3001, 3002]
    assert result[-1] == 5999
    assert time.perf_counter() - started < MAX_DURATION_S
