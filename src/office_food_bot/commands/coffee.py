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
from office_food_bot.services import BotServices


class CoffeeCommand(EffectCommand[RawArguments]):
    definition = CommandDefinition(
        "coffee",
        "позвать на кофе",
        "/coffee 15 или /coffee 16:30",
        CommandScope.GROUP,
        HelpSection.MAIN,
        additional_help=(
            CommandHelpEntry(
                "/coffee",
                "показать настройки приглашений на кофе",
                HelpSection.PROFILE_SETTINGS,
                CommandScope.PRIVATE,
            ),
            CommandHelpEntry(
                "/coffee on",
                "включить приглашения",
                HelpSection.PROFILE_SETTINGS,
                CommandScope.ANY,
            ),
            CommandHelpEntry(
                "/coffee off",
                "выключить приглашения",
                HelpSection.PROFILE_SETTINGS,
                CommandScope.ANY,
            ),
        ),
        text_aliases=("кофе",),
        scope_overrides=(
            CommandScopeOverride(CommandArgumentPattern.EMPTY, CommandScope.ANY),
            CommandScopeOverride(CommandArgumentPattern.TOGGLE, CommandScope.ANY),
        ),
        private_description="настроить приглашения на кофе",
    )

    def __init__(self, services: BotServices) -> None:
        super().__init__(RawArgumentsParser(), (), ())
        self._services = services

    async def execute_effect(
        self,
        context: CommandContext,
        request: RawArguments,
    ) -> None:
        profile = context.profile
        if profile is None:
            await context.messenger.reply(
                context.message,
                "Не вижу твой Telegram user id.",
            )
            return

        argument = (request.value or "").strip()
        if not argument:
            await context.messenger.reply(
                context.message,
                self._services.coffee.status_text(
                    profile.telegram_user_id,
                    context.message.chat.id,
                ),
            )
            return

        normalized = argument.casefold()
        if normalized in {"on", "off"}:
            await context.messenger.reply(
                context.message,
                self._services.coffee.set_invitations(
                    profile.telegram_user_id,
                    enabled=normalized == "on",
                ),
            )
            return

        error = await self._services.coffee.create_or_reschedule(
            context.bot,
            context.message.chat.id,
            profile.telegram_user_id,
            argument,
        )
        if error is not None:
            await context.messenger.reply(context.message, error)
