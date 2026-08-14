"""Hidden tests for extracted discount helper."""

from invoice import apply_discount, invoice_total


def test_helper_and_total_share_rules() -> None:
    """The helper exposes the same discount rules used by invoices."""
    assert apply_discount(100.0, "platinum") == 80.0
    assert invoice_total([40.0, 60.0], "platinum") == 80.0
