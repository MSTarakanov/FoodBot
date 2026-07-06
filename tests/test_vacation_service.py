from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from office_food_bot.database import Database
from office_food_bot.models import TelegramProfile, UserStatus
from office_food_bot.repositories import UserRepository, VacationRepository
from office_food_bot.services.vacation import (
    VACATION_DATE_FORMAT_ERROR_TEXT,
    VacationRequestKind,
    VacationService,
    parse_vacation_request,
)


def make_profile(
    telegram_user_id: int = 42,
    username: str | None = "misha",
) -> TelegramProfile:
    return TelegramProfile(
        telegram_user_id=telegram_user_id,
        username=username,
        first_name="Misha",
        last_name=None,
    )


def make_vacation_service(
    users: UserRepository,
    vacations: VacationRepository,
) -> VacationService:
    return VacationService(
        users,
        vacations,
        "Europe/Belgrade",
        clock=lambda: datetime(2026, 7, 6, 12, 0, tzinfo=ZoneInfo("Europe/Belgrade")),
    )


def test_vacation_requires_registration(
    users: UserRepository,
    database: Database,
) -> None:
    service = make_vacation_service(users, VacationRepository(database))

    assert service.reply(42, "1") == "Сначала зарегистрируйся: /register"


def test_vacation_requires_active_user(
    users: UserRepository,
    database: Database,
) -> None:
    users.create_pending_user(make_profile(), "Максим")
    service = make_vacation_service(users, VacationRepository(database))

    assert service.reply(42, "1") == "Регистрация еще ждет аппрува."

    users.approve_by_telegram_id(42)
    with database.connection:
        database.connection.execute(
            "UPDATE users SET status = ? WHERE display_name = ?",
            (UserStatus.DISABLED.value, "Максим"),
        )

    assert service.reply(42, "1") == "Регистрация сейчас неактивна."


def test_vacation_status_text_for_inactive_vacation(
    users: UserRepository,
    database: Database,
) -> None:
    users.create_pending_user(make_profile(), "Максим")
    users.approve_by_telegram_id(42)
    service = make_vacation_service(users, VacationRepository(database))

    assert service.reply(42, "") == (
        "Максим не в отпуске. Чтобы включить: /vacation 2 или /vacation 20.07"
    )


def test_vacation_day_count_one_sets_until_today(
    users: UserRepository,
    database: Database,
) -> None:
    user = users.create_pending_user(make_profile(), "Максим")
    users.approve_by_telegram_id(42)
    vacations = VacationRepository(database)
    service = make_vacation_service(users, vacations)

    assert service.reply(42, "1") == "Максим в отпуске до 06.07.2026."
    vacation = vacations.get(user.id)

    assert vacation is not None
    assert vacation.until_date == date(2026, 7, 6)


def test_vacation_zero_clears_vacation(
    users: UserRepository,
    database: Database,
) -> None:
    user = users.create_pending_user(make_profile(), "Максим")
    users.approve_by_telegram_id(42)
    vacations = VacationRepository(database)
    vacations.set_until_date(user.id, date(2026, 7, 20))
    service = make_vacation_service(users, vacations)

    assert service.reply(42, "0") == "Максим больше не в отпуске."
    assert vacations.get(user.id) is None


def test_vacation_status_ignores_expired_vacation(
    users: UserRepository,
    database: Database,
) -> None:
    user = users.create_pending_user(make_profile(), "Максим")
    users.approve_by_telegram_id(42)
    vacations = VacationRepository(database)
    vacations.set_until_date(user.id, date(2026, 7, 5))
    service = make_vacation_service(users, vacations)

    assert service.reply(42, "") == (
        "Максим не в отпуске. Чтобы включить: /vacation 2 или /vacation 20.07"
    )


def test_vacation_rejects_invalid_arguments(
    users: UserRepository,
    database: Database,
) -> None:
    users.create_pending_user(make_profile(), "Максим")
    users.approve_by_telegram_id(42)
    service = make_vacation_service(users, VacationRepository(database))

    assert service.reply(42, "wat") == VACATION_DATE_FORMAT_ERROR_TEXT
    assert service.reply(42, "-1") == VACATION_DATE_FORMAT_ERROR_TEXT
    assert service.reply(42, "367") == VACATION_DATE_FORMAT_ERROR_TEXT
    assert service.reply(42, "2026-07-05") == VACATION_DATE_FORMAT_ERROR_TEXT


def test_parse_vacation_request_supports_day_counts_and_dates() -> None:
    today = date(2026, 7, 6)

    assert parse_vacation_request("1", today).until_date == today
    assert parse_vacation_request("2", today).until_date == date(2026, 7, 7)
    assert parse_vacation_request("2026-07-20", today).until_date == date(2026, 7, 20)
    assert parse_vacation_request("20.07", today).until_date == date(2026, 7, 20)
    assert parse_vacation_request("20.07.2026", today).until_date == date(2026, 7, 20)
    assert parse_vacation_request("20/07", today).until_date == date(2026, 7, 20)
    assert parse_vacation_request("20/07/2026", today).until_date == date(2026, 7, 20)
    assert parse_vacation_request("01.01", today).until_date == date(2027, 1, 1)


def test_parse_vacation_request_zero_and_off_clear_vacation() -> None:
    today = date(2026, 7, 6)

    assert parse_vacation_request("0", today).kind == VacationRequestKind.CLEAR
    assert parse_vacation_request("off", today).kind == VacationRequestKind.CLEAR
