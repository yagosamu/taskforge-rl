"""Low-level money helpers."""

from decimal import ROUND_HALF_UP, Decimal


def price_to_cents(price: str) -> int:
    """Convert a dollar price string to integer cents."""
    cents = Decimal(price) * Decimal("100")
    return int(cents.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
