import re

from config import settings


def normalize_phone(phone):
    if not phone or not isinstance(phone, str):
        return None
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 11 and digits[0] in "78":
        digits = "7" + digits[1:]
    elif len(digits) == 10:
        digits = "7" + digits
    else:
        return None
    return digits


def _kop(value: float) -> int:
    return int(round(value * 100))


def _line(name: str, quantity: int, unit_kop: int) -> dict:
    return {
        "description": name[:128],
        "quantity": f"{quantity:.2f}",
        "amount": {"value": f"{unit_kop / 100:.2f}", "currency": "RUB"},
        "vat_code": settings.receipt_vat_code,
        "payment_mode": "full_payment",
        "payment_subject": "commodity",
    }


def build_receipt(amount: float, items: list = None, description: str = "Order",
                  email: str = None, phone: str = None) -> dict:
    customer = {"email": email or settings.receipt_email}
    phone = normalize_phone(phone)
    if phone:
        customer["phone"] = phone

    total_kop = _kop(amount)
    lines = []
    if items:
        subtotal_kop = sum(_kop(item["price"]) * int(item.get("quantity", 1)) for item in items)
        # the amount may carry a delivery fee or a discount the lines know nothing about
        factor = total_kop / subtotal_kop if subtotal_kop else 1.0
        for item in items:
            quantity = int(item.get("quantity", 1))
            lines.append([item["name"], quantity, int(round(_kop(item["price"]) * factor))])

        # unit price times quantity has to hit the total to the kopeck or yookassa rejects the
        # payment, so split one unit off the last line and put the remainder there
        diff = total_kop - sum(quantity * unit for _, quantity, unit in lines)
        if diff:
            name, quantity, unit = lines[-1]
            if quantity == 1:
                lines[-1][2] = unit + diff
            else:
                lines[-1] = [name, quantity - 1, unit]
                lines.append([name, 1, unit + diff])
    else:
        lines.append([description, 1, total_kop])

    return {"customer": customer, "items": [_line(*line) for line in lines]}
