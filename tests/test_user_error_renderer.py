from __future__ import annotations

import pytest

from office_food_bot.commands.balance import BalanceCommand
from office_food_bot.commands.error_rendering import (
    ErrorRenderContext,
    ErrorRendererRegistration,
    UserErrorRenderer,
    build_user_error_renderer,
)
from office_food_bot.user_errors import (
    BalanceError,
    BalanceErrorCode,
    CommonError,
    CommonErrorCode,
    CommonUserError,
    ExternalDependency,
    InfrastructureUnavailableError,
    UserFacingError,
)


class UnknownError(UserFacingError):
    pass


def render_fixture_error(
    error: UserFacingError,
    context: ErrorRenderContext,
) -> str:
    del error, context
    return "fixture"


def test_common_and_balance_errors_use_registered_renderers() -> None:
    renderer = build_user_error_renderer()
    context = ErrorRenderContext("foodbot_dev", BalanceCommand.definition)

    assert renderer.render(CommonError(CommonErrorCode.ADMIN_REQUIRED), context) == (
        "Команда доступна только админам."
    )
    assert (
        renderer.render(
            BalanceError(BalanceErrorCode.NO_SPLITWISE_USERS),
            context,
        )
        == "Splitwise пока не подключен."
    )
    assert (
        renderer.render(
            InfrastructureUnavailableError(ExternalDependency.SPLITWISE),
            context,
        )
        == "Не смог получить балансы Splitwise. Попробуй позже."
    )


def test_unknown_error_family_is_a_programming_error() -> None:
    renderer = build_user_error_renderer()

    with pytest.raises(RuntimeError, match="found 0"):
        renderer.render(UnknownError(), ErrorRenderContext("foodbot_dev", None))


def test_ambiguous_error_family_is_a_programming_error() -> None:
    renderer = UserErrorRenderer(
        (
            ErrorRendererRegistration(UserFacingError, render_fixture_error),
            ErrorRendererRegistration(CommonUserError, render_fixture_error),
        )
    )

    with pytest.raises(RuntimeError, match="found 2"):
        renderer.render(
            CommonError(CommonErrorCode.ADMIN_REQUIRED),
            ErrorRenderContext("foodbot_dev", None),
        )
