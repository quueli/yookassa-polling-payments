import asyncio
import logging
import uuid
from decimal import Decimal

try:
    from yookassa import Configuration, Payment
    from yookassa.domain.exceptions import ApiError, BadRequestError
    YOOKASSA_AVAILABLE = True
except ImportError:
    YOOKASSA_AVAILABLE = False

from config import settings
from database import db_manager
from money import money

logger = logging.getLogger(__name__)


class YooKassaPaymentService:
    def __init__(self, shop_id: str = None, secret_key: str = None, use_polling: bool = False, client=None):
        shop_id = shop_id or settings.yookassa_shop_id
        secret_key = secret_key or settings.yookassa_secret_key
        self.use_polling = use_polling
        self.enabled = bool(shop_id and secret_key) and (client is not None or YOOKASSA_AVAILABLE)

        if client is None and self.enabled:
            Configuration.account_id = shop_id
            Configuration.secret_key = secret_key
            client = Payment
        self.api = client

        if self.enabled:
            mode = "polling" if use_polling else "webhook"
            logger.info(f"yookassa configured for shop {shop_id}, payment status via {mode}")
        elif not YOOKASSA_AVAILABLE:
            logger.warning("yookassa sdk not installed, online payments disabled")
        else:
            logger.warning("yookassa credentials not set, online payments disabled")

    def is_enabled(self) -> bool:
        return self.enabled

    async def create_payment(self, order_id: str, amount, description: str,
                             return_url: str, receipt: dict = None):
        if not self.enabled:
            logger.error("online payments are disabled")
            return None

        amount = money(amount)
        payment_data = {
            "amount": {"value": f"{amount:.2f}", "currency": "RUB"},
            "confirmation": {"type": "redirect", "return_url": return_url},
            "capture": True,
            "description": description,
            "metadata": {"order_id": order_id},
        }
        if receipt:
            payment_data["receipt"] = receipt

        try:
            # the sdk is blocking (requests underneath), keep it off the event loop
            payment = await asyncio.to_thread(self.api.create, payment_data, str(uuid.uuid4()))
        except BadRequestError as e:
            logger.error(f"yookassa rejected payment for order {order_id}: {e}")
            return None
        except ApiError as e:
            logger.error(f"yookassa api error creating payment for order {order_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"unexpected error creating payment for order {order_id}: {e}")
            return None

        logger.info(f"payment {payment.id} created for order {order_id}")
        db_manager.set_payment_id(order_id, payment.id)

        if self.use_polling:
            from services.payment_polling import polling_service
            polling_service.add_payment_for_polling(payment.id, order_id, amount)

        return {
            "payment_id": payment.id,
            "status": payment.status,
            "amount": Decimal(payment.amount.value),
            "currency": payment.amount.currency,
            "confirmation_url": payment.confirmation.confirmation_url,
            "metadata": payment.metadata,
        }

    async def get_payment_status(self, payment_id: str):
        if not self.enabled:
            logger.error("online payments are disabled")
            return None

        try:
            payment = await asyncio.to_thread(self.api.find_one, payment_id)
        except ApiError as e:
            logger.error(f"yookassa api error reading payment {payment_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"unexpected error reading payment {payment_id}: {e}")
            return None

        return {
            "payment_id": payment.id,
            "status": payment.status,
            "paid": payment.paid,
            "amount": Decimal(payment.amount.value),
            "currency": payment.amount.currency,
            "metadata": payment.metadata,
        }


_yookassa_payment_service = None


def get_yookassa_payment_service() -> YooKassaPaymentService:
    global _yookassa_payment_service
    if _yookassa_payment_service is None:
        _yookassa_payment_service = YooKassaPaymentService(use_polling=settings.use_payment_polling)
    return _yookassa_payment_service
