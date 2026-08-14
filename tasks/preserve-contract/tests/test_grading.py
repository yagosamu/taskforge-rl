from formatters import format_invoice, format_order, format_ticket


def test_order_strips_name() -> None:
    assert format_order({"id": 1, "name": " alpha "}) == "Order:1:alpha"


def test_invoice_strips_name() -> None:
    assert format_invoice({"id": "I-9", "name": "\tAda\n"}) == "Invoice:I-9:Ada"


def test_ticket_strips_name() -> None:
    assert format_ticket({"id": 5, "name": " urgent "}) == "Ticket:5:urgent"
