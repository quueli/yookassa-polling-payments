import logging

from aiogram import Bot

from config import settings
from database import Order, db_manager

logger = logging.getLogger(__name__)

STATUS_TEXT = {
    "pending": "awaiting payment",
    "paid": "paid",
    "canceled": "canceled",
    "expired": "expired",
}


class OrderMessageManager:
    def __init__(self):
        self.admin_group_id = str(settings.admin_chat_id) if settings.admin_chat_id else None

    def _format_order_message(self, order: Order) -> str:
        lines = [
            f"Order {order.order_id}",
            f"User: {order.user_id}",
            f"Amount: {order.amount:.2f} RUB",
            f"Status: {STATUS_TEXT.get(order.status, order.status)}",
        ]
        if order.payment_id:
            lines.append(f"Payment: {order.payment_id}")
        return "\n".join(lines)

    async def send_new_order_notification(self, bot: Bot, order: Order):
        if not self.admin_group_id:
            return None

        try:
            message = await bot.send_message(
                chat_id=self.admin_group_id,
                text=self._format_order_message(order),
            )
        except Exception as e:
            logger.error(f"failed to post order {order.order_id} to admin chat: {e}")
            return None

        db_manager.update_admin_message_id(order.order_id, message.message_id)
        logger.info(f"order {order.order_id} posted to admin chat, message {message.message_id}")
        return message.message_id


order_message_manager = OrderMessageManager()
