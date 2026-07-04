from __future__ import annotations

from dataclasses import dataclass

from aiogram import Bot

from office_food_bot.config import RuntimeEnvironment, Settings


@dataclass(frozen=True)
class TelegramBotIdentity:
    telegram_bot_id: int
    username: str | None


class ProductionTokenInDevelopmentError(RuntimeError):
    pass


async def fetch_telegram_bot_identity(bot: Bot) -> TelegramBotIdentity:
    me = await bot.get_me()
    return TelegramBotIdentity(
        telegram_bot_id=me.id,
        username=me.username,
    )


async def ensure_safe_telegram_token_for_environment(
    settings: Settings,
    bot: Bot,
) -> None:
    if settings.environment == RuntimeEnvironment.PRODUCTION:
        return
    if settings.production_telegram_bot_id is None:
        return

    identity = await fetch_telegram_bot_identity(bot)
    if identity.telegram_bot_id != settings.production_telegram_bot_id:
        return

    username_text = _username_text(identity.username)
    msg = (
        "Local development is configured with the production Telegram bot token "
        f"({username_text}, id {identity.telegram_bot_id}). "
        "Create a separate development bot in @BotFather and replace TELEGRAM_BOT_TOKEN in .env."
    )
    raise ProductionTokenInDevelopmentError(msg)


def _username_text(username: str | None) -> str:
    if username is None:
        return "unknown username"
    return f"@{username}"
