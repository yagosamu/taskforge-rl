"""Order transformations."""

from module_a import price_to_cents


def discounted_lines(order: dict[str, object]) -> list[dict[str, int]]:
    """Return line totals and discounts in cents."""
    discount_rate = float(order.get("discount_rate", 0.0))
    lines: list[dict[str, int]] = []
    for item in order["items"]:  # type: ignore[index]
        unit_cents = price_to_cents(str(item["price"]))
        quantity = int(item["quantity"])
        subtotal = unit_cents * quantity
        discount = round(subtotal * discount_rate)
        lines.append({"subtotal_cents": subtotal, "discount_cents": discount})
    return lines
