import asyncio
import logging

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import settings
from database import Order, db_manager

logger = logging.getLogger(__name__)

STATUS_TEXT = {
    "pending": "awaiting payment",
    "paid": "paid",
    "canceled": "canceled",
    "expired": "expired",
    "shipped": "shipped",
    "delivered": "delivered",
}


class OrderMessageManager:
    def __init__(self):
        self.admin_group_id = self._get_admin_group_id()

    def _get_admin_group_id(self):
        if not settings.admin_chat_id:
            return None
        chat_id = str(settings.admin_chat_id)
        # the bot api wants the -100 prefix, the bare id gives "Bad Request: chat not found"
        if not chat_id.startswith("-100"):
            chat_id = "-100" + chat_id.lstrip("-")
        return chat_id

    def _get_keyboard_for_status(self, order_id: str, status: str):
        if status == "paid":
            button = InlineKeyboardButton(text="Mark shipped", callback_data=f"admin_ship_{order_id}")
        elif status == "shipped":
            button = InlineKeyboardButton(text="Mark delivered", callback_data=f"admin_deliver_{order_id}")
        else:
            return None
        return InlineKeyboardMarkup(inline_keyboard=[[button]])

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

        if order.admin_message_id:
            await self.update_order_status_message(bot, order.order_id, order.status)
            return order.admin_message_id

        try:
            message = await bot.send_message(
                chat_id=self.admin_group_id,
                text=self._format_order_message(order),
                reply_markup=self._get_keyboard_for_status(order.order_id, order.status),
            )
        except Exception as e:
            logger.error(f"failed to post order {order.order_id} to admin chat: {e}")
            return None

        await asyncio.to_thread(db_manager.update_admin_message_id, order.order_id, message.message_id)
        logger.info(f"order {order.order_id} posted to admin chat, message {message.message_id}")
        return message.message_id

    async def update_order_status_message(self, bot: Bot, order_id: str, new_status: str) -> bool:
        if not self.admin_group_id:
            return False

        order = await asyncio.to_thread(db_manager.get_order, order_id)
        if not order:
            logger.error(f"order {order_id} not found")
            return False
        if not order.admin_message_id:
            logger.warning(f"order {order_id} has no admin message to update")
            return False

        order.status = new_status
        try:
            await bot.edit_message_text(
                chat_id=self.admin_group_id,
                message_id=order.admin_message_id,
                text=self._format_order_message(order),
                reply_markup=self._get_keyboard_for_status(order_id, new_status),
            )
        except Exception as e:
            if "message is not modified" in str(e):
                return True
            logger.error(f"failed to edit admin message for order {order_id}: {e}")
            return False

        logger.info(f"admin message for order {order_id} updated, status {new_status}")
        return True


order_message_manager = OrderMessageManager()
