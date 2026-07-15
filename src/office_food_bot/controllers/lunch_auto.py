from __future__ import annotations

from office_food_bot.commanding.contracts import CommandContext
from office_food_bot.services import BotServices

GROUP_CHAT_TYPES = frozenset({"group", "supergroup"})
GROUP_ONLY_MESSAGE = "Команда доступна только в групповом чате."


async def enable_lunch_auto(context: CommandContext, services: BotServices) -> None:
    await context.state.clear()
    if not _is_group_chat(context):
        await context.messenger.reply(context.message, GROUP_ONLY_MESSAGE)
        return

    services.lunch_auto_chats.enable(
        context.message.chat.id,
        context.message.chat.title,
    )
    await context.messenger.reply(
        context.message,
        "Авто-ланч включен для этого чата.",
    )


async def disable_lunch_auto(context: CommandContext, services: BotServices) -> None:
    await context.state.clear()
    if not _is_group_chat(context):
        await context.messenger.reply(context.message, GROUP_ONLY_MESSAGE)
        return

    services.lunch_auto_chats.disable(context.message.chat.id)
    await context.messenger.reply(
        context.message,
        "Авто-ланч выключен для этого чата.",
    )


async def show_lunch_auto_status(
    context: CommandContext,
    services: BotServices,
) -> None:
    await context.state.clear()
    if not _is_group_chat(context):
        await context.messenger.reply(context.message, GROUP_ONLY_MESSAGE)
        return

    await context.messenger.reply(
        context.message,
        services.lunch_auto_chats.status_text(context.message.chat.id),
    )


def _is_group_chat(context: CommandContext) -> bool:
    return str(context.message.chat.type) in GROUP_CHAT_TYPES
