from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from office_food_bot.application.users.models import TelegramProfile
from office_food_bot.application.users.resolver import ActiveUserResolver
from office_food_bot.commanding.errors.models import (
    InputErrorCode,
)
from office_food_bot.commands.vacation import (
    VacationRequestParser,
    VacationRequestResolver,
)
from office_food_bot.database import Database
from office_food_bot.features.vacation.rendering import render_vacation_report
from office_food_bot.features.vacation.repository import VacationRepository
from office_food_bot.features.vacation.service import (
    VacationRequest,
    VacationRequestKind,
    VacationService,
    parse_vacation_request,
)
from office_food_bot.infrastructure.persistence.users import UserRepository
from office_food_bot.result import Result


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
        ActiveUserResolver(users),
        vacations,
        "Europe/Belgrade",
        clock=lambda: datetime(2026, 7, 6, 12, 0, tzinfo=ZoneInfo("Europe/Belgrade")),
    )


def vacation_text(
    service: VacationService,
    raw_argument: str,
) -> str:
    request = parsed_vacation_request(service, raw_argument)
    return render_vacation_report(service.execute(42, request)).text


def parsed_vacation_request(
    service: VacationService,
    raw_argument: str,
) -> VacationRequest:
    return VacationRequestResolver(service).resolve(
        VacationRequestParser().parse(raw_argument)
    ).fold(
        lambda request: request,
        lambda code: pytest.fail(f"Unexpected vacation parse error: {code}"),
    )


def vacation_parse_error(
    service: VacationService,
    raw_argument: str,
) -> InputErrorCode:
    result: Result[VacationRequest, InputErrorCode] = VacationRequestResolver(
        service
    ).resolve(
        VacationRequestParser().parse(raw_argument)
    )
    return result.fold(
        lambda request: pytest.fail(f"Unexpected vacation request: {request}"),
        lambda code: code,
    )


def test_vacation_status_text_for_inactive_vacation(
    users: UserRepository,
    database: Database,
) -> None:
    users.create_pending_user(make_profile(), "Максим")
    users.approve_by_telegram_id(42)
    service = make_vacation_service(users, VacationRepository(database))

    assert vacation_text(service, "") == (
        "Максим не в отпуске.\n\n"
        "Уйти в отпуск или изменить дату: /vacation 2 или /vacation 20.07\n"
        "Выйти из отпуска: /vacation 0 или /vacation off"
    )


def test_vacation_day_count_one_sets_until_today(
    users: UserRepository,
    database: Database,
) -> None:
    user = users.create_pending_user(make_profile(), "Максим")
    users.approve_by_telegram_id(42)
    vacations = VacationRepository(database)
    service = make_vacation_service(users, vacations)

    assert vacation_text(service, "1") == (
        "Максим в отпуске до 06.07.2026. Чтобы выйти из отпуска: /vacation 0"
    )
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

    assert vacation_text(service, "0") == "Максим больше не в отпуске."
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

    assert vacation_text(service, "") == (
        "Максим не в отпуске.\n\n"
        "Уйти в отпуск или изменить дату: /vacation 2 или /vacation 20.07\n"
        "Выйти из отпуска: /vacation 0 или /vacation off"
    )


def test_vacation_rejects_invalid_arguments(
    users: UserRepository,
    database: Database,
) -> None:
    users.create_pending_user(make_profile(), "Максим")
    users.approve_by_telegram_id(42)
    service = make_vacation_service(users, VacationRepository(database))

    for raw_argument in ("wat", "-1", "367", "2026-07-05"):
        assert vacation_parse_error(service, raw_argument) == InputErrorCode.INVALID_FORMAT


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
