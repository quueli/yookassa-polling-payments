import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import settings
from database import db_manager
from services.order import order_service
from services.payment import get_yookassa_payment_service
from services.payment_polling import polling_service
from services.receipt import build_receipt

PRICE = 100.0

dp = Dispatcher()


@dp.message(CommandStart())
async def start(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Pay {PRICE:.0f} RUB", callback_data="pay")]
    ])
    await message.answer("Demo shop: one button, one order.", reply_markup=keyboard)


@dp.callback_query(F.data == "pay")
async def pay(callback: CallbackQuery):
    order = db_manager.create_order(user_id=callback.from_user.id, amount=PRICE)
    me = await callback.bot.get_me()
    payment = await get_yookassa_payment_service().create_payment(
        order_id=order.order_id,
        amount=PRICE,
        description=f"Order {order.order_id}",
        return_url=f"https://t.me/{me.username}",
        receipt=build_receipt(PRICE, items=[{"name": "Demo item", "price": PRICE, "quantity": 1}]),
    )
    if not payment:
        await callback.message.edit_text("Could not create the payment, try again later.")
        await callback.answer()
        return

    url = payment["confirmation_url"]
    await callback.message.edit_text(
        f"Order {order.order_id} created.\n\nPay here: {url}\n\n"
        "The bot checks the payment on its own and writes back once it goes through."
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("admin_"))
async def admin_action(callback: CallbackQuery):
    _, action, order_id = callback.data.split("_", 2)
    status = {"ship": "shipped", "deliver": "delivered"}.get(action)
    if status and await order_service.update_order_status_with_notification(callback.bot, order_id, status):
        await callback.answer(f"Order {order_id}: {status}")
    else:
        await callback.answer("Could not update the order", show_alert=True)


async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if not settings.bot_token:
        raise SystemExit("BOT_TOKEN is not set, see .env.example")

    db_manager.create_tables()
    bot = Bot(token=settings.bot_token)
    if settings.use_payment_polling:
        await polling_service.start_polling(bot)
    try:
        await dp.start_polling(bot)
    finally:
        await polling_service.stop_polling()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
