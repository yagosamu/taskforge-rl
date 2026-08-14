"""Visible tests for pagination."""

from pagination import paginate


def test_exact_pages() -> None:
    """Items that divide evenly are paginated."""
    assert paginate([1, 2, 3, 4], 2) == [[1, 2], [3, 4]]
