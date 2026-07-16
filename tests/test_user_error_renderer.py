from __future__ import annotations

from office_food_bot.commanding.errors.models import (
    BalanceErrorCode,
    CoffeeErrorCode,
    CommonErrorCode,
    InputErrorCode,
    RegistrationErrorCode,
)
from office_food_bot.commanding.errors.rendering import (
    BalanceErrorRenderer,
    CallbackCommonErrorRenderer,
    CoffeeErrorRenderer,
    CommandInputErrorRenderer,
    CommonErrorRenderer,
    InternalErrorRenderer,
    RegistrationErrorRenderer,
)
from office_food_bot.commands.eta import EtaCommand


def test_common_error_renderer_uses_configured_bot_username() -> None:
    renderer = CommonErrorRenderer("foodbot_dev")

    assert renderer.render(CommonErrorCode.ADMIN_REQUIRED) == (
        "Команда доступна только админам."
    )
    assert renderer.render(CommonErrorCode.PRIVATE_CHAT_REQUIRED) == (
        "Команда доступна только в личке: https://t.me/foodbot_dev"
    )


def test_command_input_renderer_uses_command_definition() -> None:
    renderer = CommandInputErrorRenderer(EtaCommand.definition)

    assert renderer.render(InputErrorCode.MISSING) == (
        "Напиши через сколько минут или диапазон: /eta 20 или /eta 20-30"
    )


def test_callback_common_renderer_provides_detailed_registration_help() -> None:
    renderer = CallbackCommonErrorRenderer(CommonErrorRenderer("foodbot_dev"))

    assert renderer.render(CommonErrorCode.REGISTRATION_REQUIRED) == (
        "Чтобы пользоваться этой функцией, сначала зарегистрируйся.\n"
        "В личном чате с ботом запусти /register и пройди регистрацию сам "
        "или отправь /request_register, чтобы тебя зарегистрировал администратор."
    )
    assert renderer.render(CommonErrorCode.REGISTRATION_PENDING) == (
        "Регистрация еще ждет аппрува."
    )


def test_feature_error_renderers_accept_only_their_codes() -> None:
    assert BalanceErrorRenderer().render(BalanceErrorCode.NO_SPLITWISE_USERS) == (
        "Splitwise пока не подключен."
    )
    assert BalanceErrorRenderer().render(BalanceErrorCode.SPLITWISE_UNAVAILABLE) == (
        "Не смог получить балансы Splitwise. Попробуй позже."
    )
    assert CoffeeErrorRenderer().render(CoffeeErrorCode.SESSION_ENDED) == (
        "Эта встреча уже завершена."
    )
    assert RegistrationErrorRenderer().render(
        RegistrationErrorCode.REQUEST_ALREADY_ACTIVE
    ) == "Вы уже зарегистрированы. Если хотите отрегистрироваться, отправьте /quit."


def test_internal_error_renderer_needs_no_context() -> None:
    assert InternalErrorRenderer().render() == "Произошла ошибка. Попробуй позже."
