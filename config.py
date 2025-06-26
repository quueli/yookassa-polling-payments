from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    bot_token: str = ""
    admin_chat_id: Optional[int] = None

    database_url: str = "sqlite:///data/orders.db"

    yookassa_shop_id: Optional[str] = None
    yookassa_secret_key: Optional[str] = None

    use_payment_polling: bool = True
    polling_interval: int = 30
    max_polling_attempts: int = 120

    receipt_email: str = "receipts@example.com"
    receipt_vat_code: int = 1

    webhook_host: str = "0.0.0.0"
    webhook_port: int = 8000


settings = Settings()
