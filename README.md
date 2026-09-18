# yookassa polling

![ci](https://github.com/quueli/yookassa-polling-payments/actions/workflows/ci.yml/badge.svg)

yookassa wants a public https url for payment webhooks and my bot lived on a home box behind nat. so instead of a webhook the bot just asks yookassa about every open payment every 30 seconds until it settles. thats the whole idea.

cut out of a shop bot, the shop part is gone. what's left: the poller, the payment/order services it drives, an admin message that gets edited in place instead of spamming the chat, receipts, and a tiny demo bot.

## run

    pip install -r requirements.txt
    cp .env.example .env    # bot token + yookassa test shop id/secret
    python examples/bot.py

tests dont need network, there is a fake yookassa client:

    pytest

## things to know

- pending payments live in memory, after a restart they are restored from the orders table
- one process only. two copies of the bot would both poll the same payments
- webhook mode is still there (webhook_server.py) if you do get a domain later
- receipts assume RUB and a single vat code
