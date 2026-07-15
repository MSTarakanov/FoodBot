from __future__ import annotations

from decimal import Decimal
from typing import Protocol

from office_food_bot.balance_models import BalanceEntry, BalanceReport
from office_food_bot.commanding.errors.models import (
    BalanceError,
    BalanceErrorCode,
    ExternalDependency,
    InfrastructureUnavailableError,
)
from office_food_bot.models import ActiveSplitwiseUser, SplitwiseMember
from office_food_bot.services.splitwise import SplitwiseGroupKind, SplitwiseService

BALANCE_CURRENCY_CODE = "RSD"


class BalanceUserRepository(Protocol):
    def list_active_splitwise_users(self) -> tuple[ActiveSplitwiseUser, ...]: ...


class BalanceService:
    def __init__(
        self,
        users: BalanceUserRepository,
        splitwise: SplitwiseService,
    ) -> None:
        self._users = users
        self._splitwise = splitwise

    async def balance(self) -> BalanceReport:
        linked_users = self._users.list_active_splitwise_users()
        if not linked_users:
            raise BalanceError(BalanceErrorCode.NO_SPLITWISE_USERS)

        splitwise_result = await self._splitwise.group_members()
        if splitwise_result.kind == SplitwiseGroupKind.UNAVAILABLE:
            raise InfrastructureUnavailableError(ExternalDependency.SPLITWISE)

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
            raise BalanceError(BalanceErrorCode.NO_SPLITWISE_USERS)

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
