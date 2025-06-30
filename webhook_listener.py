import logging

from aiogram import Bot
from aiohttp import web

from config import settings
from services.order import order_service

logger = logging.getLogger(__name__)

routes = web.RouteTableDef()


@routes.post("/webhook/yookassa")
async def yookassa_webhook(request: web.Request) -> web.Response:
    data = await request.json()
    payment = data.get("object") or {}
    order_id = (payment.get("metadata") or {}).get("order_id")
    logger.info(f"webhook {data.get('event')}: order {order_id}")

    if order_id and payment.get("status") == "succeeded":
        await order_service.confirm_payment(request.app["bot"], order_id, payment["id"])
    return web.Response(text="OK")


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    app = web.Application()
    app["bot"] = Bot(token=settings.bot_token)
    app.add_routes(routes)
    web.run_app(app, host=settings.webhook_host, port=settings.webhook_port)


if __name__ == "__main__":
    main()
