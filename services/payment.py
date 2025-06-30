import asyncio
import logging
import uuid

from yookassa import Configuration, Payment
from yookassa.domain.exceptions import ApiError

from config import settings

logger = logging.getLogger(__name__)


class YooKassaPaymentService:
    def __init__(self):
        self.enabled = bool(settings.yookassa_shop_id and settings.yookassa_secret_key)
        if not self.enabled:
            logger.warning("yookassa credentials not set, online payments disabled")
            return
        Configuration.account_id = settings.yookassa_shop_id
        Configuration.secret_key = settings.yookassa_secret_key
        logger.info(f"yookassa configured for shop {settings.yookassa_shop_id}")

    def is_enabled(self) -> bool:
        return self.enabled

    async def create_payment(self, order_id: str, amount: float, description: str, return_url: str):
        if not self.enabled:
            logger.error("online payments are disabled")
            return None

        payment_data = {
            "amount": {"value": f"{amount:.2f}", "currency": "RUB"},
            "confirmation": {"type": "redirect", "return_url": return_url},
            "capture": True,
            "description": description,
            "metadata": {"order_id": order_id},
        }
        try:
            # the sdk is blocking (requests underneath), keep it off the event loop
            payment = await asyncio.to_thread(Payment.create, payment_data, str(uuid.uuid4()))
        except ApiError as e:
            logger.error(f"yookassa api error creating payment for order {order_id}: {e}")
            return None

        logger.info(f"payment {payment.id} created for order {order_id}")
        return {
            "payment_id": payment.id,
            "status": payment.status,
            "amount": float(payment.amount.value),
            "confirmation_url": payment.confirmation.confirmation_url,
        }

    async def get_payment_status(self, payment_id: str):
        if not self.enabled:
            logger.error("online payments are disabled")
            return None

        try:
            payment = await asyncio.to_thread(Payment.find_one, payment_id)
        except ApiError as e:
            logger.error(f"yookassa api error reading payment {payment_id}: {e}")
            return None

        return {
            "payment_id": payment.id,
            "status": payment.status,
            "paid": payment.paid,
            "amount": float(payment.amount.value),
            "metadata": payment.metadata,
        }


payment_service = YooKassaPaymentService()
