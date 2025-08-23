import uuid
from datetime import datetime
from types import SimpleNamespace


class FakeYooKassa:
    def __init__(self):
        self.payments = {}
        self.find_calls = 0
        self.error = None

    def create(self, params, idempotency_key=None):
        payment_id = str(uuid.uuid4())
        payment = SimpleNamespace(
            id=payment_id,
            status="pending",
            paid=False,
            amount=SimpleNamespace(value=params["amount"]["value"], currency=params["amount"]["currency"]),
            confirmation=SimpleNamespace(confirmation_url=f"https://example.com/pay/{payment_id}"),
            metadata=dict(params.get("metadata") or {}),
            description=params.get("description"),
            created_at=datetime.now(),
        )
        self.payments[payment_id] = payment
        return payment

    def find_one(self, payment_id):
        self.find_calls += 1
        if self.error:
            raise self.error
        return self.payments[payment_id]

    def set_status(self, payment_id, status):
        payment = self.payments[payment_id]
        payment.status = status
        payment.paid = status == "succeeded"
