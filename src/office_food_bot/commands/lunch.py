from __future__ import annotations

from office_food_bot.commanding.contracts import (
    CommandContext,
    EffectCommand,
    RawArguments,
    RawArgumentsParser,
)
from office_food_bot.commanding.definition import (
    CommandArgumentPattern,
    CommandDefinition,
    CommandHelpEntry,
    CommandScope,
    CommandScopeOverride,
    HelpSection,
)
from office_food_bot.commanding.profile import telegram_profile_from_message
from office_food_bot.execution import CommandExecutionMode
from office_food_bot.services import BotServices
from office_food_bot.services.lunch_polls import parse_lunch_office_selection

INVALID_LUNCH_OFFICE_MESSAGE = (
    "Не понял офис. Используй /lunch, /lunch rose, /lunch роза, "
    "/lunch skyline или /lunch скайлайн."
)


class LunchCommand(EffectCommand[RawArguments]):
    definition = CommandDefinition(
        "lunch",
        "создать опрос про обед",
        "/lunch [rose|роза|skyline|скайлайн]",
        CommandScope.GROUP,
        HelpSection.MAIN,
        additional_help=(
            CommandHelpEntry(
                "/lunch",
                "показать настройки приглашений на ланч",
                HelpSection.PROFILE_SETTINGS,
                CommandScope.PRIVATE,
            ),
            CommandHelpEntry(
                "/lunch on",
                "включить приглашения",
                HelpSection.PROFILE_SETTINGS,
                CommandScope.ANY,
            ),
            CommandHelpEntry(
                "/lunch off",
                "выключить приглашения",
                HelpSection.PROFILE_SETTINGS,
                CommandScope.ANY,
            ),
        ),
        scope_overrides=(
            CommandScopeOverride(CommandArgumentPattern.EMPTY, CommandScope.ANY),
            CommandScopeOverride(CommandArgumentPattern.TOGGLE, CommandScope.ANY),
        ),
        private_description="настроить приглашения на ланч",
    )

    def __init__(self, services: BotServices) -> None:
        super().__init__(RawArgumentsParser(), (), ())
        self._services = services

    async def execute_effect(
        self,
        context: CommandContext,
        request: RawArguments,
    ) -> None:
        await context.state.clear()
        profile = telegram_profile_from_message(context.message)
        if profile is None:
            await context.messenger.reply(
                context.message,
                "Не вижу твой Telegram user id.",
            )
            return

        argument = (request.value or "").strip().casefold()
        if argument in {"on", "off"}:
            await context.messenger.reply(
                context.message,
                self._services.invitations.set_lunch(
                    profile.telegram_user_id,
                    enabled=argument == "on",
                ),
            )
            return

        if not argument and not self._services.command_access.can_run_group_command_in_chat(
            str(context.message.chat.type),
            profile.telegram_user_id,
        ):
            await context.messenger.reply(
                context.message,
                self._services.invitations.lunch_status_text(profile.telegram_user_id),
            )
            return

        block_reason = self._services.lunch.poll_block_reason(profile.telegram_user_id)
        if block_reason is not None:
            await context.messenger.reply(context.message, block_reason)
            return

        office_selection = parse_lunch_office_selection(request.value)
        if office_selection is None:
            await context.messenger.reply(
                context.message,
                INVALID_LUNCH_OFFICE_MESSAGE,
            )
            return

        await self._services.lunch_publisher.publish(
            context.bot,
            context.message.chat.id,
            mode=CommandExecutionMode.MANUAL,
            office_selection=office_selection,
        )
