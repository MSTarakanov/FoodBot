from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import dotenv_values, find_dotenv

DEFAULT_ENV_FILE = ".env.defaults"
LOCAL_ENV_FILE = ".env"


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    database_path: str
    telegram_admin_ids: frozenset[int]
    timezone: str


def load_settings() -> Settings:
    env = _load_environment()

    token = env.get("TELEGRAM_BOT_TOKEN")
    if not token:
        msg = "TELEGRAM_BOT_TOKEN environment variable is required"
        raise RuntimeError(msg)

    return Settings(
        telegram_bot_token=token,
        database_path=env.get("DATABASE_PATH", "foodbot.sqlite3"),
        telegram_admin_ids=_parse_admin_ids(env.get("TELEGRAM_ADMIN_IDS", "")),
        timezone=env.get("FOODBOT_TIMEZONE", "Europe/Belgrade"),
    )


def _load_environment() -> dict[str, str]:
    env = _read_dotenv(DEFAULT_ENV_FILE)
    env.update(_read_dotenv(LOCAL_ENV_FILE))
    env.update(os.environ)
    return env


def _read_dotenv(filename: str) -> dict[str, str]:
    path = find_dotenv(filename, usecwd=True)
    if not path:
        return {}

    return {
        key: value
        for key, value in dotenv_values(path).items()
        if value is not None
    }


def _parse_admin_ids(raw_admin_ids: str) -> frozenset[int]:
    admin_ids: set[int] = set()
    for raw_admin_id in raw_admin_ids.split(","):
        admin_id = raw_admin_id.strip()
        if not admin_id:
            continue
        try:
            admin_ids.add(int(admin_id))
        except ValueError as error:
            msg = (
                "TELEGRAM_ADMIN_IDS must be a comma-separated list of integer Telegram user ids"
            )
            raise RuntimeError(msg) from error
    return frozenset(admin_ids)
