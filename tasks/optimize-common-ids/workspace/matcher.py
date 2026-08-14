"""Identifier matching helpers."""


def common_ids(left: list[int], right: list[int]) -> list[int]:
    """Return ids that appear in both lists, preserving left order."""
    result: list[int] = []
    for item in left:
        if item in right:
            result.append(item)
    return result
