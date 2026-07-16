from __future__ import annotations

from dataclasses import dataclass
from typing import assert_never

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
from office_food_bot.commanding.validators import (
    TelegramIdentityValidator,
    require_telegram_profile,
)
from office_food_bot.features.registration.service import RegistrationService
from office_food_bot.messaging import BotMessenger
from office_food_bot.models import ApprovalKind
from office_food_bot.result import Result, failure, success


@dataclass(frozen=True, slots=True)
class ApproveInput:
    raw_telegram_user_id: str


@dataclass(frozen=True, slots=True)
class ApproveRequest:
    telegram_user_id: int


class ApproveRequestParser:
    def parse(
        self,
        raw_arguments: str | None,
    ) -> ApproveInput:
        return ApproveInput((raw_arguments or "").strip())


class ApproveRequestResolver:
    def resolve(
        self,
        value: ApproveInput,
    ) -> Result[ApproveRequest, InputErrorCode]:
        normalized = value.raw_telegram_user_id
        if not normalized:
            return failure(InputErrorCode.MISSING)
        if not normalized.isdecimal():
            return failure(InputErrorCode.INVALID_FORMAT)
        telegram_user_id = int(normalized)
        if telegram_user_id <= 0:
            return failure(InputErrorCode.INVALID_FORMAT)
        return success(ApproveRequest(telegram_user_id))


class ApproveCommand(EffectCommand[ApproveInput, ApproveRequest]):
    definition = CommandDefinition(
        "approve",
        "подтвердить регистрацию",
        "/approve 123456789",
        CommandScope.PRIVATE,
        HelpSection.ADMINISTRATION,
        admin_only=True,
        input_errors=(
            CommandInputMessage(
                InputErrorCode.MISSING,
                "Напиши Telegram user id: /approve 123456789",
            ),
            CommandInputMessage(
                InputErrorCode.INVALID_FORMAT,
                "Telegram user id должен быть числом: /approve 123456789",
            ),
        ),
    )

    def __init__(
        self,
        messenger: BotMessenger,
        common_error_renderer: ErrorRenderer[CommonErrorCode],
        registration: RegistrationService,
    ) -> None:
        super().__init__(
            messenger,
            common_error_renderer,
            ApproveRequestParser(),
            (TelegramIdentityValidator(),),
            (),
            ApproveRequestResolver(),
        )
        self._registration = registration

    async def execute_effect(
        self,
        context: CommandContext,
        request: ApproveRequest,
    ) -> None:
        approver = require_telegram_profile(context)
        if not self._registration.can_approve(approver.telegram_user_id):
            await self._reply_common_error(context, CommonErrorCode.ADMIN_REQUIRED)
            return

        result = self._registration.approve(
            approver.telegram_user_id,
            request.telegram_user_id,
        )
        match result.kind:
            case ApprovalKind.FORBIDDEN:
                await self._reply_common_error(
                    context,
                    CommonErrorCode.ADMIN_REQUIRED,
                )
                return
            case ApprovalKind.NOT_FOUND:
                await self._messenger.reply(
                    context.message,
                    f"Не нашел заявку для Telegram ID {request.telegram_user_id}.",
                )
                return
            case ApprovalKind.APPROVED:
                approved_user = result.user
                if approved_user is None:
                    raise RuntimeError("Approved user is unexpectedly missing")
            case _:
                assert_never(result.kind)

        await self._messenger.reply(
            context.message,
            f"Аппрувнул: {approved_user.display_name}",
        )
        await self._messenger.try_send(
            context.bot,
            request.telegram_user_id,
            "Регистрация подтверждена. "
            f"Теперь я буду звать тебя {approved_user.display_name}.",
        )
