from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class BalanceEntry:
    username: str | None
    display_name: str
    amount: Decimal


@dataclass(frozen=True, slots=True)
class BalanceReport:
    entries: tuple[BalanceEntry, ...]
