"""Public invoice API."""

from module_b import discounted_lines


def invoice_summary(order: dict[str, object]) -> dict[str, int]:
    """Return subtotal, discount, and total cents for an order."""
    lines = discounted_lines(order)
    subtotal = sum(line["subtotal_cents"] for line in lines)
    discount = sum(line["discount_cents"] for line in lines)
    return {
        "subtotal_cents": subtotal,
        "discount_cents": discount,
        "total_cents": subtotal - discount,
    }
