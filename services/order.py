import logging

from aiogram import Bot

from config import settings
from database import db_manager

logger = logging.getLogger(__name__)


class OrderService:
    async def _notify_user(self, bot: Bot, user_id: int, text: str):
        try:
            await bot.send_message(chat_id=user_id, text=text)
        except Exception as e:
            # a user who blocked the bot must not stop the order from moving on
            logger.error(f"failed to notify user {user_id}: {e}")

    async def confirm_payment(self, bot: Bot, order_id: str, payment_id: str) -> bool:
        order = db_manager.get_order(order_id)
        if not order:
            logger.error(f"order {order_id} not found for payment {payment_id}")
            return False

        db_manager.update_order_status(order_id, "paid")
        logger.info(f"order {order_id} paid, payment {payment_id}")
        await self._notify_user(bot, order.user_id, f"Payment for order {order_id} received, thank you.")

        if settings.admin_chat_id:
            text = (
                f"Paid order {order_id}\n"
                f"User: {order.user_id}\n"
                f"Amount: {order.amount:.2f} RUB\n"
                f"Payment: {payment_id}"
            )
            try:
                await bot.send_message(chat_id=settings.admin_chat_id, text=text)
            except Exception as e:
                logger.error(f"failed to post order {order_id} to admin chat: {e}")
        return True

    async def cancel_unpaid(self, bot: Bot, order_id: str, status: str = "canceled") -> bool:
        order = db_manager.get_order(order_id)
        if not order or order.status != "pending":
            return False

        db_manager.update_order_status(order_id, status)
        logger.info(f"order {order_id} closed as {status}")
        await self._notify_user(bot, order.user_id, f"Order {order_id} is {status}.")
        return True


order_service = OrderService()
