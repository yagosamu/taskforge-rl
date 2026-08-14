from batches import collect_batches


def test_second_call_does_not_include_first_call() -> None:
    collect_batches([1, 2, 3], 2)

    assert collect_batches(["a"], 2) == [["a"]]


def test_empty_call_after_non_empty_call_is_empty() -> None:
    collect_batches([1], 1)

    assert collect_batches([], 3) == []


def test_returned_result_can_be_mutated_without_affecting_later_calls() -> None:
    first = collect_batches([1, 2], 1)
    first.append(["extra"])

    assert collect_batches([3], 1) == [[3]]
