import logging

from aiogram import Bot
from aiohttp import web

from config import settings
from services.order import order_service
from services.payment import get_yookassa_payment_service

logger = logging.getLogger(__name__)

BOT_KEY = web.AppKey("bot", Bot)


async def yookassa_webhook_handler(request: web.Request) -> web.Response:
    try:
        data = await request.json()
    except Exception:
        return web.Response(status=400, text="bad json")

    event = data.get("event")
    payment = data.get("object") or {}
    payment_id = payment.get("id")
    order_id = (payment.get("metadata") or {}).get("order_id")
    logger.info(f"webhook {event}: payment {payment_id}, order {order_id}")

    if not payment_id or not order_id:
        # not one of ours, but answer 200 anyway or yookassa keeps retrying it
        return web.Response(text="OK")

    # notifications are not signed, so the body is not trusted: ask the api what the payment really is
    info = await get_yookassa_payment_service().get_payment_status(payment_id)
    if not info:
        return web.Response(status=503, text="retry later")

    bot = request.app[BOT_KEY]
    if info["status"] == "succeeded":
        await order_service.confirm_payment(bot, order_id, payment_id)
    elif info["status"] == "canceled":
        await order_service.cancel_unpaid(bot, order_id, "canceled")
    return web.Response(text="OK")


async def close_bot(app: web.Application):
    await app[BOT_KEY].session.close()


def create_app(bot: Bot) -> web.Application:
    app = web.Application()
    app[BOT_KEY] = bot
    app.router.add_post("/webhook/yookassa", yookassa_webhook_handler)
    app.on_cleanup.append(close_bot)
    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if not settings.bot_token:
        raise SystemExit("BOT_TOKEN is not set, see .env.example")
    web.run_app(create_app(Bot(token=settings.bot_token)), host=settings.webhook_host, port=settings.webhook_port)
