from __future__ import annotations

import argparse
import asyncio
from collections.abc import Sequence

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import Message

from office_food_bot.config import RuntimeEnvironment, Settings, load_settings
from office_food_bot.messaging import BotMessenger
from office_food_bot.previews.registry import MESSAGE_PREVIEWS
from office_food_bot.runtime_guard import (
    ProductionTokenInDevelopmentError,
    ensure_safe_telegram_token_for_environment,
)


class PreviewError(RuntimeError):
    pass


def resolve_chat_id(settings: Settings, explicit_chat_id: int | None) -> int:
    if explicit_chat_id is not None:
        return explicit_chat_id

    admin_ids = tuple(sorted(settings.telegram_admin_ids))
    if not admin_ids:
        raise PreviewError(
            "TELEGRAM_ADMIN_IDS is empty. Re-run ./setup-dev and make yourself an admin, "
            "or pass --chat-id."
        )
    if len(admin_ids) > 1:
        ids = ", ".join(str(admin_id) for admin_id in admin_ids)
        raise PreviewError(
            f"Multiple TELEGRAM_ADMIN_IDS are configured ({ids}). Pass --chat-id explicitly."
        )
    return admin_ids[0]


async def deliver_preview(
    settings: Settings,
    raw_case: str,
    chat_id: int,
    *,
    bot: Bot | None = None,
) -> Message:
    if settings.environment != RuntimeEnvironment.DEVELOPMENT:
        raise PreviewError(
            "The local preview command only works with FOODBOT_ENV=development. "
            "Use /test in a private chat to preview messages through the production bot."
        )

    payload = MESSAGE_PREVIEWS.render(raw_case)
    if payload is None:
        available = ", ".join(MESSAGE_PREVIEWS.cases)
        raise PreviewError(f"Unknown preview case: {raw_case}. Available cases: {available}.")

    owns_bot = bot is None
    active_bot = bot or Bot(token=settings.telegram_bot_token)
    try:
        await ensure_safe_telegram_token_for_environment(settings, active_bot)
        try:
            return await BotMessenger().send_payload(active_bot, chat_id, payload)
        except TelegramForbiddenError as error:
            raise _delivery_error(settings.telegram_bot_username) from error
        except TelegramBadRequest as error:
            if "chat not found" not in str(error).casefold():
                raise
            raise _delivery_error(settings.telegram_bot_username) from error
    finally:
        if owns_bot:
            await active_bot.session.close()


def _delivery_error(bot_username: str) -> PreviewError:
    return PreviewError(
        "The bot cannot send this preview yet. "
        f"Open https://t.me/{bot_username}, press Start, and run the command again."
    )


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="preview",
        description="Send a deterministic message preview through the local development bot.",
    )
    parser.add_argument("case", help="Preview case, for example balance-full")
    parser.add_argument("--chat-id", type=int, help="Telegram chat id override")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _argument_parser()
    arguments = parser.parse_args(argv)
    try:
        settings = load_settings()
        chat_id = resolve_chat_id(settings, arguments.chat_id)
        asyncio.run(deliver_preview(settings, arguments.case, chat_id))
    except (PreviewError, ProductionTokenInDevelopmentError, RuntimeError) as error:
        parser.exit(1, f"preview: {error}\n")

    print(f"Sent {arguments.case} to Telegram chat {chat_id}.")
    return 0


def run() -> None:
    raise SystemExit(main())
