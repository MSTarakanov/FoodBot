from __future__ import annotations

from typing import Protocol, assert_never

from office_food_bot.commanding.definition import CommandDefinition
from office_food_bot.commanding.errors.models import (
    BalanceErrorCode,
    CoffeeErrorCode,
    CommonErrorCode,
    InputErrorCode,
    RegistrationErrorCode,
)


class ErrorRenderer[ErrorT](Protocol):
    def render(self, error: ErrorT) -> str: ...


class StaticErrorRenderer(Protocol):
    def render(self) -> str: ...


class CommandInputErrorRenderer:
    def __init__(self, definition: CommandDefinition) -> None:
        self._definition = definition

    def render(self, code: InputErrorCode) -> str:
        return self._definition.input_error_text(code)


class CommonErrorRenderer:
    def __init__(self, bot_username: str) -> None:
        self._bot_username = bot_username

    def render(self, code: CommonErrorCode) -> str:
        match code:
            case CommonErrorCode.MISSING_TELEGRAM_IDENTITY:
                return "Не вижу твой Telegram user id."
            case CommonErrorCode.PRIVATE_CHAT_REQUIRED:
                return (
                    "Команда доступна только в личке: "
                    f"https://t.me/{self._bot_username}"
                )
            case CommonErrorCode.GROUP_CHAT_REQUIRED:
                return "Команда доступна только в групповом чате."
            case CommonErrorCode.ADMIN_REQUIRED:
                return "Команда доступна только админам."
            case CommonErrorCode.REGISTRATION_REQUIRED:
                return "Сначала зарегистрируйся: /register"
            case CommonErrorCode.REGISTRATION_PENDING:
                return "Регистрация еще ждет аппрува."
            case CommonErrorCode.REGISTRATION_INACTIVE:
                return "Регистрация сейчас неактивна."
        assert_never(code)


class CallbackCommonErrorRenderer:
    def __init__(self, common: ErrorRenderer[CommonErrorCode]) -> None:
        self._common = common

    def render(self, code: CommonErrorCode) -> str:
        if code == CommonErrorCode.REGISTRATION_REQUIRED:
            return (
                "Чтобы пользоваться этой функцией, сначала зарегистрируйся.\n"
                "В личном чате с ботом запусти /register и пройди регистрацию сам "
                "или отправь /request_register, чтобы тебя зарегистрировал "
                "администратор."
            )
        return self._common.render(code)


class BalanceErrorRenderer:
    def render(self, code: BalanceErrorCode) -> str:
        match code:
            case BalanceErrorCode.NO_SPLITWISE_USERS:
                return "Splitwise пока не подключен."
            case BalanceErrorCode.SPLITWISE_UNAVAILABLE:
                return "Не смог получить балансы Splitwise. Попробуй позже."
        assert_never(code)


class CoffeeErrorRenderer:
    def render(self, code: CoffeeErrorCode) -> str:
        match code:
            case CoffeeErrorCode.INVALID_CALLBACK:
                return "Не понял действие."
            case CoffeeErrorCode.SESSION_ENDED:
                return "Эта встреча уже завершена."
        assert_never(code)


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


class InternalErrorRenderer:
    def render(self) -> str:
        return "Произошла ошибка. Попробуй позже."
