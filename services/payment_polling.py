import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime

from aiogram import Bot

from config import settings
from services.order import order_service
from services.payment import get_yookassa_payment_service

logger = logging.getLogger(__name__)

OPEN_STATUSES = ("pending", "waiting_for_capture")


@dataclass
class PendingPayment:
    payment_id: str
    order_id: str
    amount: float
    created_at: datetime
    last_checked: datetime
    check_count: int = 0


class YooKassaPollingService:
    def __init__(self, bot: Bot = None, payment_service=None, interval: int = None, max_attempts: int = None):
        self.bot = bot
        self.payment_service = payment_service
        self.pending_payments = {}
        self.polling_interval = interval or settings.polling_interval
        self.max_check_attempts = max_attempts or settings.max_polling_attempts
        self.pause_between_checks = 1.0
        self.is_running = False
        self._polling_task = None

    def _service(self):
        if self.payment_service is None:
            self.payment_service = get_yookassa_payment_service()
        return self.payment_service

    def add_payment_for_polling(self, payment_id: str, order_id: str, amount: float):
        if payment_id in self.pending_payments:
            return
        now = datetime.now()
        self.pending_payments[payment_id] = PendingPayment(
            payment_id=payment_id,
            order_id=order_id,
            amount=amount,
            created_at=now,
            last_checked=now,
        )
        logger.info(f"polling payment {payment_id} for order {order_id}")

    def remove_payment_from_polling(self, payment_id: str):
        pending = self.pending_payments.pop(payment_id, None)
        if pending:
            logger.info(f"stopped polling payment {payment_id} (order {pending.order_id})")

    async def check_payment_status(self, pending_payment: PendingPayment):
        info = await self._service().get_payment_status(pending_payment.payment_id)
        if not info:
            return None
        return info["status"]

    async def handle_status(self, pending_payment: PendingPayment, new_status: str) -> bool:
        if new_status == "succeeded":
            logger.info(f"payment {pending_payment.payment_id} succeeded (order {pending_payment.order_id})")
            await order_service.confirm_payment(self.bot, pending_payment.order_id, pending_payment.payment_id)
            self.remove_payment_from_polling(pending_payment.payment_id)
            return True

        if new_status == "canceled":
            logger.info(f"payment {pending_payment.payment_id} canceled (order {pending_payment.order_id})")
            await order_service.cancel_unpaid(self.bot, pending_payment.order_id, "canceled")
            self.remove_payment_from_polling(pending_payment.payment_id)
            return True

        if new_status in OPEN_STATUSES:
            return False

        logger.warning(f"unknown status {new_status} for payment {pending_payment.payment_id}")
        return False

    async def poll_once(self):
        for pending_payment in list(self.pending_payments.values()):
            if pending_payment.check_count >= self.max_check_attempts:
                logger.warning(f"payment {pending_payment.payment_id} still open, giving up")
                await order_service.cancel_unpaid(self.bot, pending_payment.order_id, "expired")
                self.remove_payment_from_polling(pending_payment.payment_id)
                continue

            status = await self.check_payment_status(pending_payment)
            if status is None:
                continue

            pending_payment.last_checked = datetime.now()
            pending_payment.check_count += 1
            if status != "pending":
                await self.handle_status(pending_payment, status)

            if self.pause_between_checks:
                await asyncio.sleep(self.pause_between_checks)

    async def polling_loop(self):
        logger.info(f"payment polling loop started, interval {self.polling_interval}s")
        while self.is_running:
            try:
                if self.pending_payments:
                    await self.poll_once()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"error in polling loop: {e}")
            await asyncio.sleep(self.polling_interval)

    async def start_polling(self, bot: Bot = None):
        if bot is not None:
            self.bot = bot
        if not self._service().is_enabled():
            logger.warning("cannot start payment polling: yookassa is not configured")
            return
        if self.is_running:
            logger.warning("payment polling already running")
            return

        self.is_running = True
        self._polling_task = asyncio.create_task(self.polling_loop())
        logger.info("payment polling started")

    async def stop_polling(self):
        if not self.is_running:
            return
        self.is_running = False
        if self._polling_task:
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                pass
        logger.info("payment polling stopped")


polling_service = YooKassaPollingService()
