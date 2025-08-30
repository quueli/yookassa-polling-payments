# yookassa polling

yookassa wants a public https url for payment webhooks and my bot lived on a home box behind nat. so instead of a webhook the bot just asks yookassa about every open payment every 30 seconds until it settles. thats the whole idea.

    pip install -r requirements.txt
    cp .env.example .env    # bot token + yookassa test shop id/secret
    python examples/bot.py
