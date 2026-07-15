from __future__ import annotations

from decimal import Decimal

import pytest
from pytest_regressions.data_regression import DataRegressionFixture

from office_food_bot.messaging import TextMessagePayload
from office_food_bot.presenters import render_balance_message
from office_food_bot.previews.balance import build_balance_full_preview
from office_food_bot.services.balances import (
    BalanceEntry,
    BalanceNotice,
    BalanceNoticeKind,
    BalanceReport,
)


def test_balance_full_payload_matches_snapshot(
    data_regression: DataRegressionFixture,
) -> None:
    payload = build_balance_full_preview()

    assert isinstance(payload, TextMessagePayload)
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


@pytest.mark.parametrize(
    ("kind", "expected_text"),
    [
        (BalanceNoticeKind.REGISTRATION_REQUIRED, "Сначала зарегистрируйся: /register"),
        (BalanceNoticeKind.REGISTRATION_PENDING, "Регистрация еще ждет аппрува."),
        (BalanceNoticeKind.REGISTRATION_INACTIVE, "Регистрация сейчас неактивна."),
        (BalanceNoticeKind.SPLITWISE_NOT_CONNECTED, "Splitwise пока не подключен."),
        (
            BalanceNoticeKind.SPLITWISE_UNAVAILABLE,
            "Не смог получить балансы Splitwise. Попробуй позже.",
        ),
    ],
)
def test_balance_notice_messages(kind: BalanceNoticeKind, expected_text: str) -> None:
    payload = render_balance_message(BalanceNotice(kind))

    assert isinstance(payload, TextMessagePayload)
    assert payload.text == expected_text


def test_balance_report_escapes_names_and_keeps_unlinked_name_plain() -> None:
    payload = render_balance_message(
        BalanceReport(
            entries=(
                BalanceEntry("linked", "Макс <Admin> & Co", Decimal("-1")),
                BalanceEntry(None, "Без username", Decimal("10")),
            )
        )
    )

    assert isinstance(payload, TextMessagePayload)
    assert '<a href="https://t.me/linked">Макс &lt;Admin&gt; &amp; Co</a>' in payload.text
    assert "· Без username" in payload.text
