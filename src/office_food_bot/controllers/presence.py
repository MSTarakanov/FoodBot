from __future__ import annotations

from office_food_bot.commanding.contracts import CommandContext, RawArguments
from office_food_bot.commanding.profile import telegram_profile_from_message
from office_food_bot.services import BotServices


async def handle_presence_command(
    context: CommandContext,
    request: RawArguments,
    services: BotServices,
) -> None:
    await context.state.clear()
    profile = telegram_profile_from_message(context.message)
    if profile is None:
        await context.messenger.reply(context.message, "Не вижу твой Telegram user id.")
        return

    command_name = context.invocation.name
    if not request.value:
        await context.messenger.reply(
            context.message,
            services.presence.eta_missing_minutes_reply(command_name),
        )
        return

    await context.messenger.reply(
        context.message,
        services.presence.eta(
            profile.telegram_user_id,
            request.value,
            command_name,
        ),
    )
