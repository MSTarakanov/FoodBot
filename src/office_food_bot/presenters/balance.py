from __future__ import annotations

from decimal import Decimal
from html import escape
from urllib.parse import quote

from aiogram.enums import ParseMode
from aiogram.types import LinkPreviewOptions

from office_food_bot.messaging import MessagePayload, TextMessagePayload
from office_food_bot.services.balances import (
    BalanceEntry,
    BalanceNotice,
    BalanceNoticeKind,
    BalanceReport,
    BalanceResult,
)

BALANCE_CURRENCY_CODE = "RSD"
BALANCE_HEADER = "<b>Балансы Splitwise</b>"
BALANCE_HIGH_DEBT_THRESHOLD = Decimal("-10000")
BALANCE_HIGH_CREDIT_THRESHOLD = Decimal("10000")
MONEY_QUANT = Decimal("0.01")
MINUS_SIGN = "\N{MINUS SIGN}"
FIGURE_SPACE = "\N{FIGURE SPACE}"
THOUSANDS_SEPARATOR = "\N{NARROW NO-BREAK SPACE}"
BALANCE_NOTICE_TEXT = {
    BalanceNoticeKind.REGISTRATION_REQUIRED: "Сначала зарегистрируйся: /register",
    BalanceNoticeKind.REGISTRATION_PENDING: "Регистрация еще ждет аппрува.",
    BalanceNoticeKind.REGISTRATION_INACTIVE: "Регистрация сейчас неактивна.",
    BalanceNoticeKind.SPLITWISE_NOT_CONNECTED: "Splitwise пока не подключен.",
    BalanceNoticeKind.SPLITWISE_UNAVAILABLE: (
        "Не смог получить балансы Splitwise. Попробуй позже."
    ),
}


def render_balance_message(result: BalanceResult) -> MessagePayload:
    if isinstance(result, BalanceNotice):
        text = BALANCE_NOTICE_TEXT[result.kind]
    elif isinstance(result, BalanceReport):
        text = _format_balance_report(result)
    else:
        raise TypeError(f"Unsupported balance result: {type(result).__name__}")
    return TextMessagePayload(
        text,
        parse_mode=ParseMode.HTML,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )


def _format_balance_report(report: BalanceReport) -> str:
    entries = sorted(
        report.entries,
        key=lambda entry: (entry.amount, entry.display_name),
    )
    integer_width = max(_integer_digit_count(entry.amount) for entry in entries)
    return "\n".join(
        (
            BALANCE_HEADER,
            "",
            *(_format_balance_entry(entry, integer_width) for entry in entries),
        )
    )


def _format_balance_entry(entry: BalanceEntry, integer_width: int) -> str:
    amount = entry.amount.quantize(MONEY_QUANT)
    formatted_amount = _format_amount(amount, integer_width)
    if amount < 0:
        formatted_amount = f"<b>{formatted_amount}</b>"
    return f"{_balance_emoji(amount)} {formatted_amount} · {_format_user_name(entry)}"


def _format_amount(amount: Decimal, integer_width: int) -> str:
    integer_part, fractional_part = f"{abs(amount):.2f}".split(".")
    alignment_prefix = _integer_alignment_prefix(len(integer_part), integer_width)
    grouped_integer = _group_integer_part(integer_part)
    sign = MINUS_SIGN if amount < 0 else "+" if amount > 0 else FIGURE_SPACE
    return (
        f"{alignment_prefix}{sign}{grouped_integer}.{fractional_part} "
        f"{BALANCE_CURRENCY_CODE}"
    )


def _integer_alignment_prefix(value_digits: int, column_digits: int) -> str:
    column_template = _group_integer_part(FIGURE_SPACE * column_digits)
    value_template = _group_integer_part(FIGURE_SPACE * value_digits)
    return column_template[: -len(value_template)]


def _group_integer_part(integer_part: str) -> str:
    groups: list[str] = []
    while integer_part:
        groups.append(integer_part[-3:])
        integer_part = integer_part[:-3]
    return THOUSANDS_SEPARATOR.join(reversed(groups))


def _integer_digit_count(amount: Decimal) -> int:
    integer_part = f"{abs(amount.quantize(MONEY_QUANT)):.2f}".partition(".")[0]
    return len(integer_part)


def _format_user_name(entry: BalanceEntry) -> str:
    display_name = escape(entry.display_name)
    if entry.username is None:
        return display_name
    profile_url = f"https://t.me/{quote(entry.username, safe='')}"
    return f'<a href="{profile_url}">{display_name}</a>'


def _balance_emoji(amount: Decimal) -> str:
    if amount < BALANCE_HIGH_DEBT_THRESHOLD:
        return "🔴"
    if amount > BALANCE_HIGH_CREDIT_THRESHOLD:
        return "🟢"
    return "⚪"
