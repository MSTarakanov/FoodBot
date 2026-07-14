from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from html import escape
from urllib.parse import quote

from office_food_bot.models import SplitwiseMember, UserStatus
from office_food_bot.repositories import UserRepository
from office_food_bot.services.splitwise import SplitwiseGroupKind, SplitwiseService

BALANCE_CURRENCY_CODE = "RSD"
BALANCE_HEADER = "<b>Балансы Splitwise</b>"
BALANCE_HIGH_DEBT_THRESHOLD = Decimal("-10000")
BALANCE_HIGH_CREDIT_THRESHOLD = Decimal("10000")
MONEY_QUANT = Decimal("0.01")
MINUS_SIGN = "\N{MINUS SIGN}"
THOUSANDS_SEPARATOR = "\N{NARROW NO-BREAK SPACE}"


@dataclass(frozen=True)
class BalanceLine:
    username: str | None
    display_name: str
    amount: Decimal


class BalanceService:
    def __init__(self, users: UserRepository, splitwise: SplitwiseService) -> None:
        self._users = users
        self._splitwise = splitwise

    async def balance(self, telegram_user_id: int) -> str:
        user = self._users.get_by_telegram_id(telegram_user_id)
        if user is None:
            return "Сначала зарегистрируйся: /register"
        if user.status == UserStatus.PENDING:
            return "Регистрация еще ждет аппрува."
        if user.status != UserStatus.ACTIVE:
            return "Регистрация сейчас неактивна."

        linked_users = self._users.list_active_splitwise_users()
        if not linked_users:
            return "Splitwise пока не подключен."

        splitwise_result = await self._splitwise.group_members()
        if splitwise_result.kind == SplitwiseGroupKind.UNAVAILABLE:
            return "Не смог получить балансы Splitwise. Попробуй позже."

        members_by_id = {
            member.splitwise_user_id: member for member in splitwise_result.members
        }
        lines = tuple(
            BalanceLine(
                linked_user.username,
                linked_user.display_name,
                _rsd_balance(member),
            )
            for linked_user in linked_users
            if (member := members_by_id.get(linked_user.splitwise_user_id)) is not None
        )
        if not lines:
            return "Splitwise пока не подключен."

        return _format_balance_lines(lines)


def _rsd_balance(member: SplitwiseMember) -> Decimal:
    return sum(
        (
            balance.amount
            for balance in member.balance
            if balance.currency_code == BALANCE_CURRENCY_CODE
        ),
        Decimal("0"),
    )


def _format_balance_lines(lines: tuple[BalanceLine, ...]) -> str:
    sorted_lines = sorted(lines, key=lambda line: (line.amount, line.display_name))
    return "\n".join(
        (
            BALANCE_HEADER,
            "",
            *(_format_balance_line(line) for line in sorted_lines),
        )
    )


def _format_balance_line(line: BalanceLine) -> str:
    amount = line.amount.quantize(MONEY_QUANT)
    formatted_amount = _format_amount(amount)
    if amount < 0:
        formatted_amount = f"<b>{formatted_amount}</b>"
    return f"{_balance_emoji(amount)} {formatted_amount} · {_format_user_name(line)}"


def _format_amount(amount: Decimal) -> str:
    absolute_amount = f"{abs(amount):,.2f}".replace(",", THOUSANDS_SEPARATOR)
    sign = MINUS_SIGN if amount < 0 else "+" if amount > 0 else ""
    return f"{sign}{absolute_amount} {BALANCE_CURRENCY_CODE}"


def _format_user_name(line: BalanceLine) -> str:
    display_name = escape(line.display_name)
    if line.username is None:
        return display_name
    profile_url = f"https://t.me/{quote(line.username, safe='')}"
    return f'<a href="{profile_url}">{display_name}</a>'


def _balance_emoji(amount: Decimal) -> str:
    if amount < BALANCE_HIGH_DEBT_THRESHOLD:
        return "🔴"
    if amount > BALANCE_HIGH_CREDIT_THRESHOLD:
        return "🟢"
    return "⚪"
