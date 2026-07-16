from __future__ import annotations

import pytest

from office_food_bot.commanding.errors.models import (
    BalanceError,
    BalanceErrorCode,
    CommandInputError,
    CommonError,
    CommonErrorCode,
    CommonUserError,
    ExternalDependency,
    InfrastructureUnavailableError,
    InputErrorCode,
    UserFacingError,
)
from office_food_bot.commanding.errors.rendering import (
    BotUsernameErrorRenderer,
    CallbackErrorRenderer,
    CommandErrorRenderer,
    ErrorRenderer,
    ErrorRendererRegistration,
    UserErrorRenderer,
    build_user_error_renderer,
)
from office_food_bot.commands.eta import EtaCommand


class UnknownError(UserFacingError):
    pass


class FixtureErrorRenderer(ErrorRenderer):
    def render(self, error: UserFacingError) -> str:
        del error
        return "fixture"


def test_common_and_balance_errors_need_no_render_context() -> None:
    renderer = build_user_error_renderer()

    assert renderer.render(CommonError(CommonErrorCode.ADMIN_REQUIRED)) == (
        "Команда доступна только админам."
    )
    assert renderer.render(BalanceError(BalanceErrorCode.NO_SPLITWISE_USERS)) == (
        "Splitwise пока не подключен."
    )
    assert renderer.render(
        InfrastructureUnavailableError(ExternalDependency.SPLITWISE)
    ) == "Не смог получить балансы Splitwise. Попробуй позже."


def test_command_renderer_uses_its_definition_for_input_error() -> None:
    renderer = CommandErrorRenderer(build_user_error_renderer(), EtaCommand.definition)

    assert renderer.render(CommandInputError(InputErrorCode.MISSING)) == (
        "Напиши через сколько минут или диапазон: /eta 20 или /eta 20-30"
    )


def test_bot_username_renderer_builds_private_chat_link() -> None:
    renderer = BotUsernameErrorRenderer(build_user_error_renderer(), "foodbot_dev")

    assert renderer.render(CommonError(CommonErrorCode.PRIVATE_CHAT_REQUIRED)) == (
        "Команда доступна только в личке: https://t.me/foodbot_dev"
    )


def test_callback_renderer_provides_detailed_registration_help() -> None:
    renderer = CallbackErrorRenderer(build_user_error_renderer())

    assert renderer.render(CommonError(CommonErrorCode.REGISTRATION_REQUIRED)) == (
        "Чтобы пользоваться этой функцией, сначала зарегистрируйся.\n"
        "В личном чате с ботом запусти /register и пройди регистрацию сам "
        "или отправь /request_register, чтобы тебя зарегистрировал администратор."
    )


def test_context_specific_errors_require_specialized_renderer() -> None:
    renderer = build_user_error_renderer()

    with pytest.raises(RuntimeError, match="CommandErrorRenderer"):
        renderer.render(CommandInputError(InputErrorCode.MISSING))
    with pytest.raises(RuntimeError, match="BotUsernameErrorRenderer"):
        renderer.render(CommonError(CommonErrorCode.PRIVATE_CHAT_REQUIRED))


def test_unknown_error_family_is_a_programming_error() -> None:
    renderer = build_user_error_renderer()

    with pytest.raises(RuntimeError, match="found 0"):
        renderer.render(UnknownError())


def test_ambiguous_error_family_is_a_programming_error() -> None:
    fixture_renderer = FixtureErrorRenderer()
    renderer = UserErrorRenderer(
        (
            ErrorRendererRegistration(UserFacingError, fixture_renderer),
            ErrorRendererRegistration(CommonUserError, fixture_renderer),
        )
    )

    with pytest.raises(RuntimeError, match="found 2"):
        renderer.render(CommonError(CommonErrorCode.ADMIN_REQUIRED))
