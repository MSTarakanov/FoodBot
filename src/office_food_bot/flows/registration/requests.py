from __future__ import annotations

from dataclasses import dataclass

from office_food_bot.commanding.contracts import CommandContext
from office_food_bot.commanding.errors.models import (
    CommandInputError,
    CommonError,
    CommonErrorCode,
    InputErrorCode,
)
from office_food_bot.services.registration import RegistrationService


@dataclass(frozen=True, slots=True)
class RegisterRequest:
    pass


@dataclass(frozen=True, slots=True)
class RegisterSelfRequest(RegisterRequest):
    pass


@dataclass(frozen=True, slots=True)
class RegisterOtherRequest(RegisterRequest):
    telegram_user_id: int


class RegisterRequestParser:
    def parse(self, raw_arguments: str | None) -> RegisterRequest:
        normalized = (raw_arguments or "").strip()
        if not normalized:
            return RegisterSelfRequest()
        if normalized.isdecimal():
            telegram_user_id = int(normalized)
            if telegram_user_id > 0:
                return RegisterOtherRequest(telegram_user_id)
        raise CommandInputError(InputErrorCode.INVALID_FORMAT)


class RegisterOtherAdminValidator:
    def __init__(self, registration: RegistrationService) -> None:
        self._registration = registration

    def validate(self, context: CommandContext, request: RegisterRequest) -> None:
        if not isinstance(request, RegisterOtherRequest):
            return
        profile = context.profile
        if profile is None:
            raise CommonError(CommonErrorCode.MISSING_TELEGRAM_IDENTITY)
        if not self._registration.can_approve(profile.telegram_user_id):
            raise CommonError(CommonErrorCode.ADMIN_REQUIRED)
