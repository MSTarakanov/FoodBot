from __future__ import annotations

from decimal import Decimal

from pytest_regressions.data_regression import DataRegressionFixture

from office_food_bot.features.balance.models import BalanceEntry, BalanceReport
from office_food_bot.features.balance.preview import build_balance_full_preview
from office_food_bot.features.balance.rendering import render_balance_message
from office_food_bot.messaging import TextMessagePayload


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
