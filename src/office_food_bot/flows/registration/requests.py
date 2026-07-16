from __future__ import annotations

from dataclasses import dataclass

from office_food_bot.commanding.contracts import CommandContext
from office_food_bot.commanding.errors.models import (
    CommonErrorCode,
    InputErrorCode,
)
from office_food_bot.result import Result, failure, success
from office_food_bot.services.registration import RegistrationService


class RegisterInput:
    pass


@dataclass(frozen=True, slots=True)
class RegisterSelfInput(RegisterInput):
    pass


@dataclass(frozen=True, slots=True)
class RegisterOtherInput(RegisterInput):
    raw_telegram_user_id: str


class RegisterRequest:
    pass


@dataclass(frozen=True, slots=True)
class RegisterSelfRequest(RegisterRequest):
    pass


@dataclass(frozen=True, slots=True)
class RegisterOtherRequest(RegisterRequest):
    telegram_user_id: int


class RegisterRequestParser:
    def parse(
        self,
        raw_arguments: str | None,
    ) -> RegisterInput:
        normalized = (raw_arguments or "").strip()
        if not normalized:
            return RegisterSelfInput()
        return RegisterOtherInput(normalized)


class RegisterRequestResolver:
    def resolve(
        self,
        value: RegisterInput,
    ) -> Result[RegisterRequest, InputErrorCode]:
        match value:
            case RegisterSelfInput():
                return success(RegisterSelfRequest())
            case RegisterOtherInput():
                if value.raw_telegram_user_id.isdecimal():
                    telegram_user_id = int(value.raw_telegram_user_id)
                    if telegram_user_id > 0:
                        return success(RegisterOtherRequest(telegram_user_id))
                return failure(InputErrorCode.INVALID_FORMAT)
            case _:
                raise RuntimeError(
                    f"Unsupported registration input: {type(value).__name__}"
                )


class RegisterOtherAdminValidator:
    def __init__(self, registration: RegistrationService) -> None:
        self._registration = registration

    def validate(
        self,
        context: CommandContext,
        request: RegisterInput,
    ) -> Result[None, CommonErrorCode]:
        match request:
            case RegisterSelfInput():
                return success(None)
            case RegisterOtherInput():
                profile = context.profile
                if profile is None:
                    return failure(CommonErrorCode.MISSING_TELEGRAM_IDENTITY)
                if not self._registration.can_approve(profile.telegram_user_id):
                    return failure(CommonErrorCode.ADMIN_REQUIRED)
                return success(None)
            case _:
                raise RuntimeError(
                    f"Unsupported registration request: {type(request).__name__}"
                )
