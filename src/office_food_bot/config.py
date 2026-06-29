import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str


def load_settings() -> Settings:
    load_dotenv()

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        msg = "TELEGRAM_BOT_TOKEN environment variable is required"
        raise RuntimeError(msg)

    return Settings(telegram_bot_token=token)
