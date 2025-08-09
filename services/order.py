import logging

from aiogram import Bot

from database import db_manager
from services.order_message_manager import order_message_manager

logger = logging.getLogger(__name__)

USER_TEXT = {
    "paid": "Payment for order {order_id} received, thank you.",
    "canceled": "Payment for order {order_id} was canceled.",
    "expired": "Order {order_id} was not paid in time and is closed.",
    "shipped": "Order {order_id} has been shipped.",
    "delivered": "Order {order_id} is delivered. Thanks for the purchase.",
}


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

        if not db_manager.mark_paid(order_id, payment_id):
            logger.info(f"order {order_id} is already {order.status}, payment {payment_id} ignored")
            return False

        logger.info(f"order {order_id} paid, payment {payment_id}")
        order = db_manager.get_order(order_id)
        await self._notify_user(bot, order.user_id, USER_TEXT["paid"].format(order_id=order_id))
        await order_message_manager.send_new_order_notification(bot, order)
        return True

    async def cancel_unpaid(self, bot: Bot, order_id: str, status: str = "canceled") -> bool:
        order = db_manager.get_order(order_id)
        if not order:
            logger.error(f"order {order_id} not found")
            return False
        if order.status != "pending":
            logger.info(f"order {order_id} is {order.status}, not closing it as {status}")
            return False

        db_manager.update_order_status(order_id, status)
        logger.info(f"order {order_id} closed as {status}")
        await self._notify_user(bot, order.user_id, USER_TEXT[status].format(order_id=order_id))
        if order.admin_message_id:
            await order_message_manager.update_order_status_message(bot, order_id, status)
        return True

    async def update_order_status_with_notification(self, bot: Bot, order_id: str, new_status: str) -> bool:
        order = db_manager.get_order(order_id)
        if not order:
            return False
        if not db_manager.update_order_status(order_id, new_status):
            return False

        await order_message_manager.update_order_status_message(bot, order_id, new_status)
        if new_status in USER_TEXT:
            await self._notify_user(bot, order.user_id, USER_TEXT[new_status].format(order_id=order_id))
        logger.info(f"order {order_id} -> {new_status}")
        return True


order_service = OrderService()
