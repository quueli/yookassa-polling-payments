from decimal import Decimal

from money import from_kop, money, to_kop


def test_float_noise_is_rounded_away():
    assert money(0.1 + 0.2) == Decimal("0.30")
    assert to_kop(0.1 + 0.2) == 30


def test_half_kopeck_rounds_up():
    assert to_kop("1.005") == 101
    assert money("2.675") == Decimal("2.68")


def test_kopecks_round_trip():
    assert from_kop(to_kop("1234.56")) == Decimal("1234.56")


def test_order_amount_is_decimal(db):
    order = db.create_order(user_id=1, amount=199.99)
    assert order.amount == Decimal("199.99")
    assert isinstance(order.amount, Decimal)
    assert order.amount_kop == 19999
