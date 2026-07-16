from __future__ import annotations

from dataclasses import dataclass

from office_food_bot.commanding.contracts import (
    CommandContext,
    EffectCommand,
)
from office_food_bot.commanding.definition import CommandDefinition, CommandScope, HelpSection
from office_food_bot.commanding.errors.models import CommonErrorCode, InputErrorCode
from office_food_bot.commanding.errors.rendering import ErrorRenderer
from office_food_bot.messaging import BotMessenger
from office_food_bot.previews.catalog import MessagePreviewCatalog
from office_food_bot.result import Result, success


@dataclass(frozen=True, slots=True)
class PreviewRequest:
    case_name: str


class PreviewRequestParser:
    def parse(
        self,
        raw_arguments: str | None,
    ) -> Result[PreviewRequest, InputErrorCode]:
        return success(PreviewRequest((raw_arguments or "").strip().casefold()))


class TestCommand(EffectCommand[PreviewRequest]):
    definition = CommandDefinition(
        "test",
        "отправить тестовое сообщение",
        "/test balance-full",
        CommandScope.PRIVATE,
        HelpSection.ADMINISTRATION,
        admin_only=True,
        show_in_menu=False,
    )

    def __init__(
        self,
        messenger: BotMessenger,
        common_error_renderer: ErrorRenderer[CommonErrorCode],
        previews: MessagePreviewCatalog,
    ) -> None:
        super().__init__(
            messenger,
            common_error_renderer,
            PreviewRequestParser(),
            (),
            (),
        )
        self._previews = previews

    async def execute_effect(
        self,
        context: CommandContext,
        request: PreviewRequest,
    ) -> None:
        payload = self._previews.render(request.case_name)
        if payload is None:
            await self._messenger.reply(
                context.message,
                self._previews.help_text(),
            )
            return

        await self._messenger.reply_payload(context.message, payload)
