import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime

from aiogram import Bot

from config import settings
from services.order import order_service
from services.payment import payment_service

logger = logging.getLogger(__name__)


@dataclass
class PendingPayment:
    payment_id: str
    order_id: str
    amount: float
    created_at: datetime
    check_count: int = 0


class YooKassaPollingService:
    def __init__(self, bot: Bot = None):
        self.bot = bot
        self.pending_payments = {}
        self.polling_interval = settings.polling_interval
        self.is_running = False
        self._polling_task = None

    def add_payment_for_polling(self, payment_id: str, order_id: str, amount: float):
        if payment_id in self.pending_payments:
            return
        self.pending_payments[payment_id] = PendingPayment(
            payment_id=payment_id,
            order_id=order_id,
            amount=amount,
            created_at=datetime.now(),
        )
        logger.info(f"polling payment {payment_id} for order {order_id}")

    def remove_payment_from_polling(self, payment_id: str):
        self.pending_payments.pop(payment_id, None)

    async def poll_once(self):
        for pending in list(self.pending_payments.values()):
            info = await payment_service.get_payment_status(pending.payment_id)
            if not info:
                continue
            pending.check_count += 1

            if info["status"] == "succeeded":
                logger.info(f"payment {pending.payment_id} succeeded (order {pending.order_id})")
                await order_service.confirm_payment(self.bot, pending.order_id, pending.payment_id)
                self.remove_payment_from_polling(pending.payment_id)
            elif info["status"] == "canceled":
                await order_service.cancel_unpaid(self.bot, pending.order_id, "canceled")
                self.remove_payment_from_polling(pending.payment_id)

            await asyncio.sleep(1)

    async def polling_loop(self):
        while self.is_running:
            try:
                if self.pending_payments:
                    await self.poll_once()
            except Exception as e:
                logger.error(f"error in polling loop: {e}")
            await asyncio.sleep(self.polling_interval)

    async def start_polling(self, bot: Bot = None):
        if bot is not None:
            self.bot = bot
        if self.is_running:
            return
        self.is_running = True
        self._polling_task = asyncio.create_task(self.polling_loop())
        logger.info("payment polling started")

    async def stop_polling(self):
        self.is_running = False
        if self._polling_task:
            self._polling_task.cancel()


polling_service = YooKassaPollingService()
