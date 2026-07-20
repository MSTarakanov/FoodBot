from __future__ import annotations

from enum import StrEnum
from typing import assert_never


class RegistrationErrorCode(StrEnum):
    REQUEST_ALREADY_PENDING = "request_already_pending"
    REQUEST_ALREADY_ACTIVE = "request_already_active"
    REQUEST_UNAVAILABLE = "request_unavailable"


class RegistrationErrorRenderer:
    def render(self, code: RegistrationErrorCode) -> str:
        match code:
            case RegistrationErrorCode.REQUEST_ALREADY_PENDING:
                return (
                    "Заявка уже ждет аппрува. "
                    "Если хотите отменить регистрацию, отправьте /quit."
                )
            case RegistrationErrorCode.REQUEST_ALREADY_ACTIVE:
                return (
                    "Вы уже зарегистрированы. "
                    "Если хотите отрегистрироваться, отправьте /quit."
                )
            case RegistrationErrorCode.REQUEST_UNAVAILABLE:
                return (
                    "Регистрация сейчас недоступна. "
                    "Если хотите отрегистрироваться, отправьте /quit."
                )
        assert_never(code)
