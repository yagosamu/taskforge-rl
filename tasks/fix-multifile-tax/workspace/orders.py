"""Order totals."""

from pricing import tax_rate


def order_total(subtotal: float, state: str) -> float:
    """Return subtotal plus state sales tax."""
    return round(subtotal * (1 + tax_rate(state)), 2)
