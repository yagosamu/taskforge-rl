from module_c import invoice_summary


def test_rounds_half_cent_up_before_discount() -> None:
    order = {"items": [{"price": "1.005", "quantity": 1}], "discount_rate": 0}

    assert invoice_summary(order)["subtotal_cents"] == 101


def test_rounds_each_unit_before_multiplying() -> None:
    order = {"items": [{"price": "0.335", "quantity": 3}], "discount_rate": 0}

    assert invoice_summary(order)["subtotal_cents"] == 102


def test_discount_uses_rounded_subtotal() -> None:
    order = {"items": [{"price": "10.005", "quantity": 2}], "discount_rate": 0.1}

    assert invoice_summary(order) == {
        "subtotal_cents": 2002,
        "discount_cents": 200,
        "total_cents": 1802,
    }
