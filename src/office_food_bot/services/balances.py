from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from office_food_bot.models import SplitwiseMember, UserStatus
from office_food_bot.repositories import UserRepository
from office_food_bot.services.splitwise import SplitwiseGroupKind, SplitwiseService

BALANCE_CURRENCY_CODE = "RSD"


@dataclass(frozen=True)
class BalanceEntry:
    username: str | None
    display_name: str
    amount: Decimal


class BalanceResult:
    pass


@dataclass(frozen=True)
class BalanceReport(BalanceResult):
    entries: tuple[BalanceEntry, ...]


class BalanceNoticeKind(StrEnum):
    REGISTRATION_REQUIRED = "registration_required"
    REGISTRATION_PENDING = "registration_pending"
    REGISTRATION_INACTIVE = "registration_inactive"
    SPLITWISE_NOT_CONNECTED = "splitwise_not_connected"
    SPLITWISE_UNAVAILABLE = "splitwise_unavailable"


@dataclass(frozen=True)
class BalanceNotice(BalanceResult):
    kind: BalanceNoticeKind


class BalanceService:
    def __init__(self, users: UserRepository, splitwise: SplitwiseService) -> None:
        self._users = users
        self._splitwise = splitwise

    async def balance(self, telegram_user_id: int) -> BalanceResult:
        user = self._users.get_by_telegram_id(telegram_user_id)
        if user is None:
            return BalanceNotice(BalanceNoticeKind.REGISTRATION_REQUIRED)
        if user.status == UserStatus.PENDING:
            return BalanceNotice(BalanceNoticeKind.REGISTRATION_PENDING)
        if user.status != UserStatus.ACTIVE:
            return BalanceNotice(BalanceNoticeKind.REGISTRATION_INACTIVE)

        linked_users = self._users.list_active_splitwise_users()
        if not linked_users:
            return BalanceNotice(BalanceNoticeKind.SPLITWISE_NOT_CONNECTED)

        splitwise_result = await self._splitwise.group_members()
        if splitwise_result.kind == SplitwiseGroupKind.UNAVAILABLE:
            return BalanceNotice(BalanceNoticeKind.SPLITWISE_UNAVAILABLE)

        members_by_id = {
            member.splitwise_user_id: member for member in splitwise_result.members
        }
        entries = tuple(
            BalanceEntry(
                linked_user.username,
                linked_user.display_name,
                _rsd_balance(member),
            )
            for linked_user in linked_users
            if (member := members_by_id.get(linked_user.splitwise_user_id)) is not None
        )
        if not entries:
            return BalanceNotice(BalanceNoticeKind.SPLITWISE_NOT_CONNECTED)

        return BalanceReport(entries)


def _rsd_balance(member: SplitwiseMember) -> Decimal:
    return sum(
        (
            balance.amount
            for balance in member.balance
            if balance.currency_code == BALANCE_CURRENCY_CODE
        ),
        Decimal("0"),
    )
