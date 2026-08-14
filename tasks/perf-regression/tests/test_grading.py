import time

from lookup import common_active_ids


def test_preserves_left_order_and_deduplicates() -> None:
    left = [
        {"id": "b", "active": True},
        {"id": "a", "active": True},
        {"id": "b", "active": True},
    ]
    right = [{"id": "a", "active": True}, {"id": "b", "active": True}]

    assert common_active_ids(left, right) == ["b", "a"]


def test_requires_active_on_both_sides() -> None:
    left = [{"id": 1, "active": True}, {"id": 2, "active": False}]
    right = [{"id": 1, "active": False}, {"id": 2, "active": True}]

    assert common_active_ids(left, right) == []


def test_large_input_runtime() -> None:
    left = [{"id": index, "active": True} for index in range(6000)]
    right = [{"id": index, "active": True} for index in range(3000, 9000)]
    started = time.perf_counter()

    result = common_active_ids(left, right)

    assert result[:3] == [3000, 3001, 3002]
    assert result[-1] == 5999
    assert time.perf_counter() - started < 0.25
