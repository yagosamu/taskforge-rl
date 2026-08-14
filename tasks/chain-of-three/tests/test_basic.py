from module_c import invoice_summary


def test_integer_cent_prices() -> None:
    order = {"items": [{"price": "2.50", "quantity": 2}], "discount_rate": 0.1}

    assert invoice_summary(order) == {
        "subtotal_cents": 500,
        "discount_cents": 50,
        "total_cents": 450,
    }
