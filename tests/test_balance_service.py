from __future__ import annotations

from decimal import Decimal

import pytest

from office_food_bot.balance_models import BalanceEntry, BalanceReport
from office_food_bot.commanding.errors.models import BalanceErrorCode
from office_food_bot.models import (
    ActiveSplitwiseUser,
    SplitwiseBalance,
    SplitwiseMember,
)
from office_food_bot.result import Result
from office_food_bot.services.balances import BalanceService
from office_food_bot.services.splitwise import SplitwiseService, SplitwiseUnavailableError


class FakeSplitwiseClient:
    def __init__(
        self,
        members: tuple[SplitwiseMember, ...] = (),
        *,
        unavailable: bool = False,
    ) -> None:
        self._members = members
        self._unavailable = unavailable

    async def group_members(self, group_id: int) -> tuple[SplitwiseMember, ...]:
        if self._unavailable:
            raise SplitwiseUnavailableError("Splitwise is unavailable")
        return self._members


class FakeBalanceUserRepository:
    def __init__(self, users: tuple[ActiveSplitwiseUser, ...] = ()) -> None:
        self._users = users

    def list_active_splitwise_users(self) -> tuple[ActiveSplitwiseUser, ...]:
        return self._users


def make_member(
    splitwise_user_id: int,
    amount: str,
    *,
    currency_code: str = "RSD",
) -> SplitwiseMember:
    return SplitwiseMember(
        splitwise_user_id=splitwise_user_id,
        first_name="Splitwise",
        last_name=None,
        email=f"{splitwise_user_id}@example.com",
        balance=(
            SplitwiseBalance(
                currency_code=currency_code,
                amount=Decimal(amount),
            ),
        ),
    )


def make_service(
    users: tuple[ActiveSplitwiseUser, ...] = (),
    members: tuple[SplitwiseMember, ...] = (),
    *,
    unavailable: bool = False,
) -> BalanceService:
    return BalanceService(
        FakeBalanceUserRepository(users),
        SplitwiseService(FakeSplitwiseClient(members, unavailable=unavailable), 55),
    )


def make_user(
    splitwise_user_id: int,
    display_name: str,
    username: str | None,
) -> ActiveSplitwiseUser:
    return ActiveSplitwiseUser(
        username=username,
        display_name=display_name,
        splitwise_user_id=splitwise_user_id,
        email=f"{splitwise_user_id}@example.com",
    )


async def test_balance_returns_placeholder_when_splitwise_is_empty() -> None:
    assert balance_error(await make_service().balance()) == (
        BalanceErrorCode.NO_SPLITWISE_USERS
    )


async def test_balance_builds_report_from_active_users_and_splitwise_balances() -> None:
    result = await make_service(
        (
            make_user(1002, "Антон", "user43"),
            make_user(1001, "Максим", "user42"),
            make_user(1004, "Олег", "user45"),
            make_user(1003, "Тимофей", "user44"),
        ),
        (
            make_member(1001, "277.967"),
            make_member(1002, "-10837.88"),
            make_member(1003, "18976.74"),
            make_member(1004, "6028.75"),
        ),
    ).balance()

    assert balance_report(result) == BalanceReport(
        entries=(
            BalanceEntry("user43", "Антон", Decimal("-10837.88")),
            BalanceEntry("user42", "Максим", Decimal("277.967")),
            BalanceEntry("user45", "Олег", Decimal("6028.75")),
            BalanceEntry("user44", "Тимофей", Decimal("18976.74")),
        )
    )


async def test_balance_builds_group_report_without_requester_data() -> None:
    assert balance_report(
        await make_service(
            (make_user(1002, "Антон", "user43"),),
            (make_member(1002, "-100.50"),),
        ).balance()
    ) == BalanceReport(
        entries=(BalanceEntry("user43", "Антон", Decimal("-100.50")),)
    )


async def test_balance_ignores_non_rsd_and_uses_zero_when_rsd_is_missing() -> None:
    assert balance_report(
        await make_service(
            (make_user(1001, "Максим", "user42"),),
            (make_member(1001, "10.00", currency_code="EUR"),),
        ).balance()
    ) == BalanceReport(entries=(BalanceEntry("user42", "Максим", Decimal("0")),))


async def test_balance_preserves_user_display_name_in_report() -> None:
    assert balance_report(
        await make_service(
            (make_user(1001, "Макс <Admin> & Co", "user42"),),
            (make_member(1001, "-1.00"),),
        ).balance()
    ) == BalanceReport(
        entries=(BalanceEntry("user42", "Макс <Admin> & Co", Decimal("-1.00")),)
    )


async def test_balance_does_not_mention_linked_user_without_username() -> None:
    assert balance_report(
        await make_service(
            (make_user(1001, "Максим", None),),
            (make_member(1001, "10.00"),),
        ).balance()
    ) == BalanceReport(
        entries=(BalanceEntry(None, "Максим", Decimal("10.00")),)
    )


async def test_balance_skips_linked_users_missing_from_splitwise_response() -> None:
    assert balance_error(
        await make_service((make_user(1001, "Максим", "user42"),)).balance()
    ) == BalanceErrorCode.NO_SPLITWISE_USERS


async def test_balance_returns_unavailable_when_splitwise_fails() -> None:
    assert balance_error(
        await make_service(
            (make_user(1001, "Максим", "user42"),),
            unavailable=True,
        ).balance()
    ) == BalanceErrorCode.SPLITWISE_UNAVAILABLE


def balance_report(
    result: Result[BalanceReport, BalanceErrorCode],
) -> BalanceReport:
    return result.fold(
        lambda report: report,
        lambda code: pytest.fail(f"Unexpected balance error: {code}"),
    )


def balance_error(
    result: Result[BalanceReport, BalanceErrorCode],
) -> BalanceErrorCode:
    return result.fold(
        lambda report: pytest.fail(f"Unexpected balance report: {report}"),
        lambda code: code,
    )
