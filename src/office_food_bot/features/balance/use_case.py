from __future__ import annotations

from decimal import Decimal
from typing import Protocol, assert_never

from office_food_bot.application.splitwise.models import SplitwiseMember
from office_food_bot.features.balance.errors import BalanceErrorCode
from office_food_bot.features.balance.models import (
    ActiveSplitwiseUser,
    BalanceEntry,
    BalanceReport,
)
from office_food_bot.integrations.splitwise import SplitwiseGroupKind, SplitwiseService
from office_food_bot.result import Result, failure, success

BALANCE_CURRENCY_CODE = "RSD"


class BalanceUserRepository(Protocol):
    def list_active_splitwise_users(self) -> tuple[ActiveSplitwiseUser, ...]: ...


class GetBalanceReport:
    def __init__(
        self,
        users: BalanceUserRepository,
        splitwise: SplitwiseService,
    ) -> None:
        self._users = users
        self._splitwise = splitwise

    async def execute(self) -> Result[BalanceReport, BalanceErrorCode]:
        linked_users = self._users.list_active_splitwise_users()
        if not linked_users:
            return failure(BalanceErrorCode.NO_SPLITWISE_USERS)

        splitwise_result = await self._splitwise.group_members()
        match splitwise_result.kind:
            case SplitwiseGroupKind.UNAVAILABLE:
                return failure(BalanceErrorCode.SPLITWISE_UNAVAILABLE)
            case SplitwiseGroupKind.AVAILABLE:
                pass
            case _:
                assert_never(splitwise_result.kind)

        members_by_id = {member.splitwise_user_id: member for member in splitwise_result.members}
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
            return failure(BalanceErrorCode.NO_SPLITWISE_USERS)

        return success(BalanceReport(entries))


def _rsd_balance(member: SplitwiseMember) -> Decimal:
    return sum(
        (
            balance.amount
            for balance in member.balance
            if balance.currency_code == BALANCE_CURRENCY_CODE
        ),
        Decimal("0"),
    )
