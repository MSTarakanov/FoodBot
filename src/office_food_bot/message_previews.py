from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from office_food_bot.messaging import TextMessagePayload
from office_food_bot.services.balances import BalanceLine, BalanceMessageRenderer


class PreviewCase(StrEnum):
    BALANCE_FULL = "balance-full"


BALANCE_FULL_LINES = (
    BalanceLine("preview_alex", "Алексей", Decimal("-12500.00")),
    BalanceLine("preview_olga", "Ольга", Decimal("-7536.37")),
    BalanceLine("preview_anton", "Антон", Decimal("-2083.70")),
    BalanceLine(None, "Без username", Decimal("0")),
    BalanceLine("preview_tim", "Тимофей", Decimal("68.36")),
    BalanceLine("preview_max", "Максим", Decimal("277.97")),
    BalanceLine("preview_albert", "Альберт", Decimal("6028.75")),
    BalanceLine("preview_sergey", "Сергей", Decimal("11925.78")),
)


@dataclass(frozen=True, slots=True)
class MessagePreviewCatalog:
    balance_renderer: BalanceMessageRenderer

    @property
    def cases(self) -> tuple[PreviewCase, ...]:
        return tuple(PreviewCase)

    def render(self, raw_case: str) -> TextMessagePayload | None:
        try:
            preview_case = PreviewCase(raw_case.strip().casefold())
        except ValueError:
            return None

        if preview_case == PreviewCase.BALANCE_FULL:
            return self.balance_renderer.render(BALANCE_FULL_LINES)

        return None

    def help_text(self) -> str:
        commands = "\n".join(f"/test {case.value}" for case in self.cases)
        return f"Доступные тестовые сообщения:\n{commands}"


MESSAGE_PREVIEWS = MessagePreviewCatalog(BalanceMessageRenderer())
