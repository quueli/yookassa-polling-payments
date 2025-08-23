import re

from config import settings


def normalize_phone(phone):
    if not phone or not isinstance(phone, str):
        return None
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 11 and digits[0] in "78":
        return "7" + digits[1:]
    if len(digits) == 10:
        return "7" + digits
    return None


def build_receipt(amount: float, description: str = "Order", email: str = None, phone: str = None) -> dict:
    customer = {"email": email or settings.receipt_email}
    phone = normalize_phone(phone)
    if phone:
        customer["phone"] = phone

    return {
        "customer": customer,
        "items": [
            {
                "description": description[:128],
                "quantity": "1.00",
                "amount": {"value": f"{amount:.2f}", "currency": "RUB"},
                "vat_code": settings.receipt_vat_code,
                "payment_mode": "full_payment",
                "payment_subject": "commodity",
            }
        ],
    }
