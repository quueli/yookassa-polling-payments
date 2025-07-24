import asyncio
import sys

from services.payment import get_yookassa_payment_service

USAGE = "usage: python -m scripts.check_payment <payment_id>"


async def main(payment_id: str) -> int:
    info = await get_yookassa_payment_service().get_payment_status(payment_id)
    if not info:
        print("no answer from yookassa, see the log above")
        return 1
    for key, value in info.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(USAGE)
    sys.exit(asyncio.run(main(sys.argv[1])))
