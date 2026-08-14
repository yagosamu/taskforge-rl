"""Visible order total tests."""

from orders import order_total


def test_california_total() -> None:
    """California totals use the known tax rate."""
    assert order_total(100.0, "CA") == 107.5
