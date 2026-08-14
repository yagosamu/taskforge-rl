"""Invoice pricing logic."""


def apply_discount(subtotal: float, customer_tier: str) -> float:
    """Return subtotal after applying the customer tier discount."""
    return subtotal


def invoice_total(items: list[float], customer_tier: str) -> float:
    """Return the total price for invoice items."""
    subtotal = sum(items)
    if customer_tier == "gold":
        subtotal *= 0.9
    elif customer_tier == "platinum":
        subtotal *= 0.8
    return round(subtotal, 2)
