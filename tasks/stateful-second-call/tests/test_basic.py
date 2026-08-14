from batches import collect_batches


def test_single_call_batches_items() -> None:
    assert collect_batches([1, 2, 3], 2) == [[1, 2], [3]]
