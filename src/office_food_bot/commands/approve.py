from __future__ import annotations

from office_food_bot.commanding.contracts import (
    CommandContext,
    EffectCommand,
    RawArguments,
    RawArgumentsParser,
)
from office_food_bot.commanding.definition import CommandDefinition, CommandScope, HelpSection
from office_food_bot.models import ApprovalKind
from office_food_bot.services import BotServices


class ApproveCommand(EffectCommand[RawArguments]):
    definition = CommandDefinition(
        "approve",
        "подтвердить регистрацию",
        "/approve 123456789",
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
        approver = context.profile
        if approver is None:
            await context.messenger.reply(
                context.message,
                "Не вижу твой Telegram user id.",
            )
            return

        if not request.value:
            await context.messenger.reply(
                context.message,
                "Напиши Telegram user id: /approve 123456789",
            )
            return

        try:
            telegram_user_id = int(request.value.strip())
        except ValueError:
            await context.messenger.reply(
                context.message,
                "Telegram user id должен быть числом: /approve 123456789",
            )
            return

        result = self._services.registration.approve(
            approver.telegram_user_id,
            telegram_user_id,
        )
        if result.kind == ApprovalKind.FORBIDDEN:
            await context.messenger.reply(
                context.message,
                "Не могу: аппрувить могут только админы.",
            )
            return

        if result.kind == ApprovalKind.NOT_FOUND:
            await context.messenger.reply(
                context.message,
                f"Не нашел заявку для Telegram ID {telegram_user_id}.",
            )
            return

        approved_user = result.user
        if approved_user is None:
            raise RuntimeError("Approved user is unexpectedly missing")

        await context.messenger.reply(
            context.message,
            f"Аппрувнул: {approved_user.display_name}",
        )
        await context.messenger.try_send(
            context.bot,
            telegram_user_id,
            "Регистрация подтверждена. "
            f"Теперь я буду звать тебя {approved_user.display_name}.",
        )
