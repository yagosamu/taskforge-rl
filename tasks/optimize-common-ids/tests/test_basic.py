"""Visible matcher tests."""

from matcher import common_ids


def test_common_ids_small() -> None:
    """Small inputs return common ids in left order."""
    assert common_ids([3, 1, 2], [2, 3]) == [3, 2]
