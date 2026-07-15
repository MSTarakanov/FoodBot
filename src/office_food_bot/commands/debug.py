from __future__ import annotations

from office_food_bot.commanding.contracts import (
    CommandContext,
    EffectCommand,
    RawArguments,
    RawArgumentsParser,
)
from office_food_bot.commanding.definition import CommandDefinition, CommandScope, HelpSection
from office_food_bot.commanding.menu import setup_private_admin_commands
from office_food_bot.services import BotServices

DEBUG_ON_VALUES = frozenset({"1", "on", "true", "вкл"})
DEBUG_OFF_VALUES = frozenset({"0", "off", "false", "выкл"})


def _debug_status_text(enabled: bool) -> str:
    if enabled:
        return "Debug: включен."
    return "Debug: выключен."


class DebugCommand(EffectCommand[RawArguments]):
    definition = CommandDefinition(
        "debug",
        "включить или выключить debug режим",
        "/debug 1",
        CommandScope.PRIVATE,
        HelpSection.ADMINISTRATION,
        admin_only=True,
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

        raw_argument = (request.value or "").strip().casefold()
        if not raw_argument:
            await context.messenger.reply(
                context.message,
                _debug_status_text(
                    self._services.debug.is_enabled(profile.telegram_user_id)
                ),
            )
            return

        if raw_argument in DEBUG_ON_VALUES:
            self._services.debug.set_enabled(profile.telegram_user_id, True)
            await self._update_menu(context, profile.telegram_user_id)
            await context.messenger.reply(
                context.message,
                "Debug включен. В личке доступны все команды.",
            )
            return

        if raw_argument in DEBUG_OFF_VALUES:
            self._services.debug.set_enabled(profile.telegram_user_id, False)
            await self._update_menu(context, profile.telegram_user_id)
            await context.messenger.reply(context.message, "Debug выключен.")
            return

        await context.messenger.reply(
            context.message,
            "Напиши /debug 1 или /debug 0",
        )

    async def _update_menu(
        self,
        context: CommandContext,
        telegram_user_id: int,
    ) -> None:
        await setup_private_admin_commands(
            context.bot,
            self._services.command_access,
            context.catalog,
            telegram_user_id,
        )
