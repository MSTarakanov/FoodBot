from __future__ import annotations

from decimal import Decimal

from office_food_bot.messaging import MessagePayload
from office_food_bot.presenters import render_balance_message
from office_food_bot.previews.catalog import PreviewDefinition
from office_food_bot.services.balances import BalanceEntry, BalanceReport


def build_balance_full_preview() -> MessagePayload:
    return render_balance_message(
        BalanceReport(
            entries=(
                BalanceEntry("preview_alex", "Алексей", Decimal("-12500.00")),
                BalanceEntry("preview_olga", "Ольга", Decimal("-7536.37")),
                BalanceEntry("preview_anton", "Антон", Decimal("-2083.70")),
                BalanceEntry(None, "Без username", Decimal("0")),
                BalanceEntry("preview_tim", "Тимофей", Decimal("68.36")),
                BalanceEntry("preview_max", "Максим", Decimal("277.97")),
                BalanceEntry("preview_albert", "Альберт", Decimal("6028.75")),
                BalanceEntry("preview_sergey", "Сергей", Decimal("11925.78")),
            )
        )
    )


BALANCE_FULL_PREVIEW = PreviewDefinition(
    name="balance-full",
    build=build_balance_full_preview,
)
