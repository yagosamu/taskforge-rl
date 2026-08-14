"""Visible tests for invoice totals."""

from invoice import invoice_total


def test_invoice_total_gold() -> None:
    """Existing invoice total behavior stays intact."""
    assert invoice_total([50.0, 50.0], "gold") == 90.0
