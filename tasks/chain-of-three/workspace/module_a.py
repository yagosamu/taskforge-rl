"""Low-level money helpers."""


def price_to_cents(price: str) -> int:
    """Convert a dollar price string to integer cents."""
    return int(float(price) * 100)
