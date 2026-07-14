from __future__ import annotations

from decimal import Decimal

from office_food_bot.models import SplitwiseBalance, SplitwiseMember, TelegramProfile
from office_food_bot.repositories import UserRepository
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


def make_profile(
    telegram_user_id: int = 42,
    username: str | None = "misha",
    first_name: str = "Misha",
) -> TelegramProfile:
    return TelegramProfile(
        telegram_user_id=telegram_user_id,
        username=username,
        first_name=first_name,
        last_name=None,
    )


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
    users: UserRepository,
    members: tuple[SplitwiseMember, ...] = (),
    *,
    unavailable: bool = False,
) -> BalanceService:
    return BalanceService(
        users,
        SplitwiseService(FakeSplitwiseClient(members, unavailable=unavailable), 55),
    )


def save_active_splitwise_user(
    users: UserRepository,
    *,
    telegram_user_id: int,
    display_name: str,
    splitwise_user_id: int,
) -> None:
    users.save_pending_registration(
        make_profile(
            telegram_user_id=telegram_user_id,
            username=f"user{telegram_user_id}",
            first_name=display_name,
        ),
        display_name,
        SplitwiseMember(
            splitwise_user_id=splitwise_user_id,
            first_name="Splitwise",
            last_name=None,
            email=f"{splitwise_user_id}@example.com",
        ),
    )
    users.approve_by_telegram_id(telegram_user_id)


async def test_balance_requires_registration(users: UserRepository) -> None:
    assert await make_service(users).balance(42) == "Сначала зарегистрируйся: /register"


async def test_balance_requires_approved_registration(users: UserRepository) -> None:
    users.create_pending_user(make_profile(), "Максим")

    assert await make_service(users).balance(42) == "Регистрация еще ждет аппрува."


async def test_balance_returns_placeholder_when_splitwise_is_empty(
    users: UserRepository,
) -> None:
    users.create_pending_user(make_profile(), "Максим")
    users.approve_by_telegram_id(42)

    assert await make_service(users).balance(42) == "Splitwise пока не подключен."


async def test_balance_formats_active_linked_users_by_rsd_debt_order(
    users: UserRepository,
) -> None:
    save_active_splitwise_user(
        users,
        telegram_user_id=42,
        display_name="Максим",
        splitwise_user_id=1001,
    )
    save_active_splitwise_user(
        users,
        telegram_user_id=43,
        display_name="Антон",
        splitwise_user_id=1002,
    )
    save_active_splitwise_user(
        users,
        telegram_user_id=44,
        display_name="Тимофей",
        splitwise_user_id=1003,
    )

    result = await make_service(
        users,
        (
            make_member(1001, "277.967"),
            make_member(1002, "-10837.88"),
            make_member(1003, "18976.74"),
        ),
    ).balance(42)

    assert result == (
        "Текущая ситуация по балансам в Splitwise:\n"
        "\n"
        '🔴 <a href="tg://user?id=43">Антон</a>: <b>-10837.88 RSD</b>\n'
        '⚪ <a href="tg://user?id=42">Максим</a>: +277.97 RSD\n'
        '🟢 <a href="tg://user?id=44">Тимофей</a>: +18976.74 RSD'
    )


async def test_balance_active_user_without_splitwise_link_can_view_group_balance(
    users: UserRepository,
) -> None:
    users.create_pending_user(make_profile(), "Максим")
    users.approve_by_telegram_id(42)
    save_active_splitwise_user(
        users,
        telegram_user_id=43,
        display_name="Антон",
        splitwise_user_id=1002,
    )

    assert await make_service(users, (make_member(1002, "-100.50"),)).balance(42) == (
        "Текущая ситуация по балансам в Splitwise:\n"
        "\n"
        '⚪ <a href="tg://user?id=43">Антон</a>: <b>-100.50 RSD</b>'
    )


async def test_balance_ignores_non_rsd_and_uses_zero_when_rsd_is_missing(
    users: UserRepository,
) -> None:
    save_active_splitwise_user(
        users,
        telegram_user_id=42,
        display_name="Максим",
        splitwise_user_id=1001,
    )

    assert await make_service(users, (make_member(1001, "10.00", currency_code="EUR"),)).balance(
        42
    ) == (
        "Текущая ситуация по балансам в Splitwise:\n"
        "\n"
        '⚪ <a href="tg://user?id=42">Максим</a>: 0.00 RSD'
    )


async def test_balance_escapes_linked_user_display_name(users: UserRepository) -> None:
    save_active_splitwise_user(
        users,
        telegram_user_id=42,
        display_name="Макс <Admin> & Co",
        splitwise_user_id=1001,
    )

    assert await make_service(users, (make_member(1001, "-1.00"),)).balance(42) == (
        "Текущая ситуация по балансам в Splitwise:\n"
        "\n"
        '⚪ <a href="tg://user?id=42">Макс &lt;Admin&gt; &amp; Co</a>: '
        "<b>-1.00 RSD</b>"
    )


async def test_balance_skips_linked_users_missing_from_splitwise_response(
    users: UserRepository,
) -> None:
    save_active_splitwise_user(
        users,
        telegram_user_id=42,
        display_name="Максим",
        splitwise_user_id=1001,
    )

    assert await make_service(users).balance(42) == "Splitwise пока не подключен."


async def test_balance_returns_unavailable_when_splitwise_fails(
    users: UserRepository,
) -> None:
    save_active_splitwise_user(
        users,
        telegram_user_id=42,
        display_name="Максим",
        splitwise_user_id=1001,
    )

    assert await make_service(users, unavailable=True).balance(42) == (
        "Не смог получить балансы Splitwise. Попробуй позже."
    )
