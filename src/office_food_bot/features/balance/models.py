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


@dataclass(frozen=True)
class ActiveSplitwiseUser:
    username: str | None
    display_name: str
    splitwise_user_id: int
    email: str | None
