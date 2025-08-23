from services.receipt import build_receipt, normalize_phone


def total(receipt):
    return round(sum(float(item["amount"]["value"]) * float(item["quantity"]) for item in receipt["items"]), 2)


def test_single_line_without_items():
    receipt = build_receipt(150.5, description="Order 1")
    assert len(receipt["items"]) == 1
    assert receipt["items"][0]["amount"]["value"] == "150.50"
    assert receipt["items"][0]["description"] == "Order 1"
    assert receipt["customer"]["email"]


def test_lines_add_up():
    items = [{"name": "A", "price": 33.33, "quantity": 3}]
    receipt = build_receipt(100.0, items)
    assert total(receipt) == 100.0
    assert [item["quantity"] for item in receipt["items"]] == ["2.00", "1.00"]


def test_delivery_fee_spread():
    items = [{"name": "A", "price": 100, "quantity": 1}, {"name": "B", "price": 50, "quantity": 2}]
    receipt = build_receipt(250.0, items)
    assert total(receipt) == 250.0
    assert all(float(item["amount"]["value"]) > 0 for item in receipt["items"])


def test_phone_normalization():
    assert normalize_phone("8 (900) 123-45-67") == "79001234567"
    assert normalize_phone("+7 900 123 45 67") == "79001234567"
    assert normalize_phone("9001234567") == "79001234567"
    assert normalize_phone("12345") is None
    assert normalize_phone(None) is None


def test_bad_phone_is_dropped():
    assert "phone" not in build_receipt(10.0, phone="12345")["customer"]
    assert build_receipt(10.0, phone="8 900 123 45 67")["customer"]["phone"] == "79001234567"
