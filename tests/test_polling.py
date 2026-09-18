import asyncio
from types import SimpleNamespace

import pytest

from fake_yookassa import FakeYooKassa
from services.order import order_service
from services.payment import YooKassaPaymentService
from services.payment_polling import YooKassaPollingService

USER_ID = 123456789
ADMIN_CHAT = "-1001234567890"
RETURN_URL = "https://example.com/back"


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def env(db, bot):
    fake = FakeYooKassa()
    service = YooKassaPaymentService(shop_id="test", secret_key="test", use_polling=False, client=fake)
    poller = YooKassaPollingService(bot=bot, payment_service=service, interval=1, max_attempts=3)
    poller.pause_between_checks = 0
    return SimpleNamespace(db=db, bot=bot, fake=fake, service=service, poller=poller)


def new_payment(env, amount=100.0, add_to_poller=True):
    order = env.db.create_order(user_id=USER_ID, amount=amount)
    data = run(env.service.create_payment(order.order_id, amount, "test order", return_url=RETURN_URL))
    if add_to_poller:
        env.poller.add_payment_for_polling(data["payment_id"], order.order_id, amount)
    return order, data["payment_id"]


def test_pending_then_succeeded(env):
    order, payment_id = new_payment(env)

    run(env.poller.poll_once())
    assert env.db.get_order(order.order_id).status == "pending"
    assert env.poller.pending_payments[payment_id].check_count == 1
    assert env.bot.messages == []

    env.fake.set_status(payment_id, "succeeded")
    run(env.poller.poll_once())

    order = env.db.get_order(order.order_id)
    assert order.status == "paid"
    assert order.payment_id == payment_id
    assert payment_id not in env.poller.pending_payments

    user_messages = env.bot.messages_to(USER_ID)
    assert len(user_messages) == 1 and "received" in user_messages[0].text

    admin_messages = env.bot.messages_to(ADMIN_CHAT)
    assert len(admin_messages) == 1
    assert "Status: paid" in admin_messages[0].text
    assert order.admin_message_id == admin_messages[0].message_id


def test_canceled(env):
    order, payment_id = new_payment(env)
    env.fake.set_status(payment_id, "canceled")

    run(env.poller.poll_once())

    assert env.db.get_order(order.order_id).status == "canceled"
    assert payment_id not in env.poller.pending_payments
    assert "canceled" in env.bot.messages_to(USER_ID)[0].text
    assert env.bot.messages_to(ADMIN_CHAT) == []


def test_expires_after_max_attempts(env):
    order, payment_id = new_payment(env)

    for _ in range(3):
        run(env.poller.poll_once())
    assert env.db.get_order(order.order_id).status == "pending"
    assert env.poller.pending_payments[payment_id].check_count == 3

    run(env.poller.poll_once())

    assert env.db.get_order(order.order_id).status == "expired"
    assert payment_id not in env.poller.pending_payments
    assert "not paid in time" in env.bot.messages_to(USER_ID)[0].text
    assert env.fake.find_calls == 3


def test_api_error_is_not_an_attempt(env):
    order, payment_id = new_payment(env)

    env.fake.error = RuntimeError("yookassa is down")
    for _ in range(5):
        run(env.poller.poll_once())
    assert env.poller.pending_payments[payment_id].check_count == 0
    assert env.db.get_order(order.order_id).status == "pending"

    env.fake.error = None
    env.fake.set_status(payment_id, "succeeded")
    run(env.poller.poll_once())
    assert env.db.get_order(order.order_id).status == "paid"


def test_restart_recovery(env):
    order, payment_id = new_payment(env, add_to_poller=False)

    poller = YooKassaPollingService(bot=env.bot, payment_service=env.service, max_attempts=3)
    poller.pause_between_checks = 0
    assert run(poller.restore_pending_payments()) >= 1
    assert payment_id in poller.pending_payments
    assert run(poller.restore_pending_payments()) == 0

    env.fake.set_status(payment_id, "succeeded")
    run(poller.poll_once())
    assert env.db.get_order(order.order_id).status == "paid"
    assert payment_id not in poller.pending_payments


def test_no_double_confirm(env):
    order, payment_id = new_payment(env)
    env.fake.set_status(payment_id, "succeeded")

    assert run(order_service.confirm_payment(env.bot, order.order_id, payment_id)) is True
    assert run(order_service.confirm_payment(env.bot, order.order_id, payment_id)) is False

    run(env.poller.poll_once())
    assert payment_id not in env.poller.pending_payments

    assert len(env.bot.messages_to(USER_ID)) == 1
    assert len(env.bot.messages_to(ADMIN_CHAT)) == 1
    assert env.db.get_order(order.order_id).status == "paid"


def test_paid_order_is_not_closed(env):
    order, payment_id = new_payment(env)
    env.fake.set_status(payment_id, "succeeded")
    run(env.poller.poll_once())

    assert run(order_service.cancel_unpaid(env.bot, order.order_id, "expired")) is False
    assert run(order_service.cancel_unpaid(env.bot, order.order_id, "canceled")) is False
    assert env.db.get_order(order.order_id).status == "paid"


def test_late_payment_after_expiry(env):
    order, payment_id = new_payment(env)
    run(order_service.cancel_unpaid(env.bot, order.order_id, "expired"))
    assert env.db.get_order(order.order_id).status == "expired"

    assert run(order_service.confirm_payment(env.bot, order.order_id, payment_id)) is True
    assert env.db.get_order(order.order_id).status == "paid"
    assert len(env.bot.messages_to(ADMIN_CHAT)) == 1
