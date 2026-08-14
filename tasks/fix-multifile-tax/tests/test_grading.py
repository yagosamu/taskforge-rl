"""Hidden order total tests."""

from orders import order_total


def test_new_york_total() -> None:
    """New York totals should use the New York tax rate."""
    assert order_total(100.0, "NY") == 108.0
