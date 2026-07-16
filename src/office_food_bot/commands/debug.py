from __future__ import annotations

from dataclasses import dataclass

from office_food_bot.commanding.access import CommandAccessService
from office_food_bot.commanding.catalog import CommandCatalogProvider
from office_food_bot.commanding.contracts import (
    CommandContext,
    EffectCommand,
)
from office_food_bot.commanding.definition import (
    CommandDefinition,
    CommandInputMessage,
    CommandScope,
    HelpSection,
)
from office_food_bot.commanding.errors.models import (
    CommandInputError,
    CommonError,
    CommonErrorCode,
    InputErrorCode,
)
from office_food_bot.commanding.menu import setup_private_admin_commands
from office_food_bot.commanding.validators import (
    TelegramIdentityValidator,
    require_telegram_profile,
)
from office_food_bot.messaging import BotMessenger
from office_food_bot.services.debug import DebugService

DEBUG_ON_VALUES = frozenset({"1", "on", "true", "вкл"})
DEBUG_OFF_VALUES = frozenset({"0", "off", "false", "выкл"})


@dataclass(frozen=True, slots=True)
class DebugRequest:
    pass


@dataclass(frozen=True, slots=True)
class DebugStatusRequest(DebugRequest):
    pass


@dataclass(frozen=True, slots=True)
class DebugToggleRequest(DebugRequest):
    enabled: bool


class DebugRequestParser:
    def parse(self, raw_arguments: str | None) -> DebugRequest:
        normalized = (raw_arguments or "").strip().casefold()
        if not normalized:
            return DebugStatusRequest()
        if normalized in DEBUG_ON_VALUES:
            return DebugToggleRequest(True)
        if normalized in DEBUG_OFF_VALUES:
            return DebugToggleRequest(False)
        raise CommandInputError(InputErrorCode.INVALID_CHOICE)


def _debug_status_text(enabled: bool) -> str:
    if enabled:
        return "Debug: включен."
    return "Debug: выключен."


class DebugCommand(EffectCommand[DebugRequest]):
    definition = CommandDefinition(
        "debug",
        "включить или выключить debug режим",
        "/debug 1",
        CommandScope.PRIVATE,
        HelpSection.ADMINISTRATION,
        admin_only=True,
        input_errors=(
            CommandInputMessage(
                InputErrorCode.INVALID_CHOICE,
                "Напиши /debug 1 или /debug 0",
            ),
        ),
    )

    def __init__(
        self,
        messenger: BotMessenger,
        debug: DebugService,
        access: CommandAccessService,
        catalog: CommandCatalogProvider,
    ) -> None:
        super().__init__(
            messenger,
            DebugRequestParser(),
            (TelegramIdentityValidator(),),
            (),
        )
        self._debug = debug
        self._access = access
        self._catalog = catalog

    async def execute_effect(
        self,
        context: CommandContext,
        request: DebugRequest,
    ) -> None:
        profile = require_telegram_profile(context)
        if not self._access.is_admin(profile.telegram_user_id):
            raise CommonError(CommonErrorCode.ADMIN_REQUIRED)

        if isinstance(request, DebugStatusRequest):
            await self._messenger.reply(
                context.message,
                _debug_status_text(self._debug.is_enabled(profile.telegram_user_id)),
            )
            return

        if not isinstance(request, DebugToggleRequest):
            raise RuntimeError(f"Unsupported debug request: {type(request).__name__}")
        self._debug.set_enabled(profile.telegram_user_id, request.enabled)
        await self._update_menu(context, profile.telegram_user_id)
        reply = (
            "Debug включен. В личке доступны все команды."
            if request.enabled
            else "Debug выключен."
        )
        await self._messenger.reply(context.message, reply)

    async def _update_menu(
        self,
        context: CommandContext,
        telegram_user_id: int,
    ) -> None:
        await setup_private_admin_commands(
            context.bot,
            self._access,
            self._catalog(),
            telegram_user_id,
        )
