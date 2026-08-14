"""Hidden tests for pagination."""

from pagination import paginate


def test_trailing_item_is_kept() -> None:
    """The final partial page is not dropped."""
    assert paginate([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]
