from __future__ import annotations

from enum import StrEnum
from typing import assert_never


class BalanceErrorCode(StrEnum):
    NO_SPLITWISE_USERS = "no_splitwise_users"
    SPLITWISE_UNAVAILABLE = "splitwise_unavailable"


class BalanceErrorRenderer:
    def render(self, code: BalanceErrorCode) -> str:
        match code:
            case BalanceErrorCode.NO_SPLITWISE_USERS:
                return "Splitwise пока не подключен."
            case BalanceErrorCode.SPLITWISE_UNAVAILABLE:
                return "Не смог получить балансы Splitwise. Попробуй позже."
        assert_never(code)
