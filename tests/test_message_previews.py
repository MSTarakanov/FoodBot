from __future__ import annotations

from pytest_regressions.data_regression import DataRegressionFixture

from office_food_bot.message_previews import BALANCE_FULL_LINES, MESSAGE_PREVIEWS
from office_food_bot.services.balances import BalanceMessageRenderer


def test_balance_full_payload_matches_snapshot(
    data_regression: DataRegressionFixture,
) -> None:
    payload = MESSAGE_PREVIEWS.render("balance-full")

    assert payload is not None
    data_regression.check(
        {
            "method": "sendMessage",
            "text": payload.text,
            "parse_mode": payload.parse_mode.value if payload.parse_mode is not None else None,
            "link_preview_options": {
                "is_disabled": payload.link_preview_options.is_disabled
                if payload.link_preview_options is not None
                else None,
            },
        }
    )


def test_balance_preview_uses_production_renderer() -> None:
    assert MESSAGE_PREVIEWS.render("balance-full") == BalanceMessageRenderer().render(
        BALANCE_FULL_LINES
    )


def test_preview_catalog_rejects_unknown_case_and_lists_available_cases() -> None:
    assert MESSAGE_PREVIEWS.render("unknown") is None
    assert MESSAGE_PREVIEWS.help_text() == (
        "Доступные тестовые сообщения:\n/test balance-full"
    )
