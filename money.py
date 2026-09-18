from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def money(value) -> Decimal:
    # str() first: Decimal(0.1) is 0.1000000000000000055511151231257827
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def to_kop(value) -> int:
    return int((money(value) * 100).to_integral_value(rounding=ROUND_HALF_UP))


def from_kop(kop: int) -> Decimal:
    return (Decimal(kop) / 100).quantize(CENT)
