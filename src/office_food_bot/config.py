from __future__ import annotations

import os
from dataclasses import dataclass
from enum import StrEnum

from dotenv import dotenv_values, find_dotenv

DEFAULT_ENV_FILE = ".env.defaults"
LOCAL_ENV_FILE = ".env"


class RuntimeEnvironment(StrEnum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"


@dataclass(frozen=True)
class Settings:
    environment: RuntimeEnvironment
    telegram_bot_token: str
    telegram_bot_username: str
    database_path: str
    telegram_admin_ids: frozenset[int]
    timezone: str
    splitwise_api_key: str | None
    splitwise_group_id: int | None
    production_telegram_bot_id: int | None


def load_settings() -> Settings:
    env = _load_environment()

    return Settings(
        environment=_parse_environment(_required_env_value(env, "FOODBOT_ENV")),
        telegram_bot_token=_required_env_value(env, "TELEGRAM_BOT_TOKEN"),
        telegram_bot_username=_parse_telegram_bot_username(
            _required_env_value(env, "TELEGRAM_BOT_USERNAME")
        ),
        database_path=_required_env_value(env, "DATABASE_PATH"),
        telegram_admin_ids=_parse_admin_ids(
            _required_env_value(env, "TELEGRAM_ADMIN_IDS", allow_empty=True)
        ),
        timezone=_required_env_value(env, "FOODBOT_TIMEZONE"),
        splitwise_api_key=_optional_env_value(env, "SPLITWISE_API_KEY"),
        splitwise_group_id=_parse_optional_int(env, "SPLITWISE_GROUP_ID"),
        production_telegram_bot_id=_parse_optional_int(env, "PRODUCTION_TELEGRAM_BOT_ID"),
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


def _required_env_value(
    env: dict[str, str],
    name: str,
    *,
    allow_empty: bool = False,
) -> str:
    value = env.get(name)
    if value is None or (not allow_empty and not value):
        msg = f"{name} environment variable is required"
        raise RuntimeError(msg)
    return value


def _optional_env_value(env: dict[str, str], name: str) -> str | None:
    value = env.get(name)
    if value is None or not value.strip():
        return None
    return value.strip()


def _parse_optional_int(env: dict[str, str], name: str) -> int | None:
    value = _optional_env_value(env, name)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError as error:
        msg = f"{name} must be an integer"
        raise RuntimeError(msg) from error


def _parse_environment(raw_environment: str) -> RuntimeEnvironment:
    try:
        return RuntimeEnvironment(raw_environment)
    except ValueError as error:
        msg = "FOODBOT_ENV must be either development or production"
        raise RuntimeError(msg) from error


def _parse_telegram_bot_username(raw_username: str) -> str:
    username = raw_username.strip().removeprefix("@")
    if not username:
        msg = "TELEGRAM_BOT_USERNAME environment variable is required"
        raise RuntimeError(msg)
    if not username.replace("_", "").isalnum():
        msg = "TELEGRAM_BOT_USERNAME must contain only letters, digits, and underscores"
        raise RuntimeError(msg)
    return username


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
