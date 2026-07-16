from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class SplitwiseBalance:
    currency_code: str
    amount: Decimal


@dataclass(frozen=True)
class SplitwiseMember:
    splitwise_user_id: int
    first_name: str
    last_name: str | None
    email: str
    balance: tuple[SplitwiseBalance, ...] = ()
