from __future__ import annotations

from dataclasses import dataclass

from office_food_bot.boolean_input import parse_toggle
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
    CommonErrorCode,
    InputErrorCode,
)
from office_food_bot.commanding.errors.rendering import ErrorRenderer
from office_food_bot.commanding.menu import setup_private_admin_commands
from office_food_bot.commanding.validators import (
    TelegramIdentityValidator,
    require_telegram_profile,
)
from office_food_bot.messaging import BotMessenger
from office_food_bot.result import Result, failure, success
from office_food_bot.services.debug import DebugService


class DebugInput:
    pass


@dataclass(frozen=True, slots=True)
class DebugStatusInput(DebugInput):
    pass


@dataclass(frozen=True, slots=True)
class DebugToggleInput(DebugInput):
    raw_value: str


class DebugRequest:
    pass


@dataclass(frozen=True, slots=True)
class DebugStatusRequest(DebugRequest):
    pass


@dataclass(frozen=True, slots=True)
class DebugToggleRequest(DebugRequest):
    enabled: bool


class DebugRequestParser:
    def parse(
        self,
        raw_arguments: str | None,
    ) -> DebugInput:
        normalized = (raw_arguments or "").strip().casefold()
        if not normalized:
            return DebugStatusInput()
        return DebugToggleInput(normalized)


class DebugRequestResolver:
    def resolve(
        self,
        value: DebugInput,
    ) -> Result[DebugRequest, InputErrorCode]:
        match value:
            case DebugStatusInput():
                return success(DebugStatusRequest())
            case DebugToggleInput():
                enabled = parse_toggle(value.raw_value, allow_numeric=True)
                if enabled is None:
                    return failure(InputErrorCode.INVALID_CHOICE)
                return success(DebugToggleRequest(enabled))
            case _:
                raise RuntimeError(f"Unsupported debug input: {type(value).__name__}")


def _debug_status_text(enabled: bool) -> str:
    if enabled:
        return "Debug: включен."
    return "Debug: выключен."


class DebugCommand(EffectCommand[DebugInput, DebugRequest]):
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
        common_error_renderer: ErrorRenderer[CommonErrorCode],
        debug: DebugService,
        access: CommandAccessService,
        catalog: CommandCatalogProvider,
    ) -> None:
        super().__init__(
            messenger,
            common_error_renderer,
            DebugRequestParser(),
            (TelegramIdentityValidator(),),
            (),
            DebugRequestResolver(),
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
            await self._reply_common_error(context, CommonErrorCode.ADMIN_REQUIRED)
            return

        match request:
            case DebugStatusRequest():
                await self._messenger.reply(
                    context.message,
                    _debug_status_text(
                        self._debug.is_enabled(profile.telegram_user_id)
                    ),
                )
            case DebugToggleRequest():
                self._debug.set_enabled(profile.telegram_user_id, request.enabled)
                await self._update_menu(context, profile.telegram_user_id)
                reply = (
                    "Debug включен. В личке доступны все команды."
                    if request.enabled
                    else "Debug выключен."
                )
                await self._messenger.reply(context.message, reply)
            case _:
                raise RuntimeError(
                    f"Unsupported debug request: {type(request).__name__}"
                )

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
