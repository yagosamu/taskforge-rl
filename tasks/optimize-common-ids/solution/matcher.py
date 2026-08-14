"""Identifier matching helpers."""


def common_ids(left: list[int], right: list[int]) -> list[int]:
    """Return ids that appear in both lists, preserving left order."""
    right_ids = set(right)
    return [item for item in left if item in right_ids]
