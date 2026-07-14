from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from office_food_bot.database import Database
from office_food_bot.models import (
    PollKind,
    StoredPoll,
    TelegramProfile,
)
from office_food_bot.poll_options import PollOption
from office_food_bot.repositories import PollRepository, UserRepository
from office_food_bot.services.lunch_attendance import LunchAttendanceService
from office_food_bot.services.poll_tracking import PollTrackingService
from office_food_bot.services.polls import (
    PollDefinition,
    PollDefinitionCatalog,
)


def test_poll_selection_stores_key_independently_of_display_text(
    database: Database,
) -> None:
    definition = PollDefinition(
        kind=PollKind.LUNCH_ATTENDANCE_V1,
        question="Question",
        options=(PollOption.LUNCH_EAT_IN_OFFICE,),
        allows_multiple_answers=False,
    )
    service = PollTrackingService(
        PollRepository(database),
        PollDefinitionCatalog((definition,)),
        clock=lambda: datetime(2026, 7, 7, 10, tzinfo=UTC),
    )
    service.register_poll("poll-1", -100, 10, definition, date(2026, 7, 7))

    service.consume_action_requests("poll-1", 42, (0,))

    row = database.connection.execute(
        "SELECT option_key FROM poll_selected_options WHERE poll_id = 'poll-1'"
    ).fetchone()
    assert row is not None
    assert row["option_key"] == PollOption.LUNCH_EAT_IN_OFFICE.value
    assert (
        PollOption.LUNCH_EAT_IN_OFFICE.display_value
        == "кушаю в офисе"
    )
    assert row["option_key"] != PollOption.LUNCH_EAT_IN_OFFICE.display_value


def test_lunch_attendance_uses_latest_poll_for_chat_and_date(
    database: Database,
) -> None:
    users = UserRepository(database)
    for telegram_id, name in (
        (42, "Максим"),
        (43, "Анна"),
        (44, "Борис"),
        (45, "Вера"),
    ):
        users.create_pending_user(
            TelegramProfile(telegram_id, name.casefold(), name, None),
            name,
        )
        users.approve_by_telegram_id(telegram_id)
    polls = PollRepository(database)
    context_date = date(2026, 7, 7)
    polls.save(
        StoredPoll(
            "old-attendance",
            -100,
            10,
            PollKind.LUNCH_ATTENDANCE_V1,
            context_date,
            datetime(2026, 7, 7, 9, tzinfo=UTC),
        )
    )
    polls.save(
        StoredPoll(
            "new-attendance",
            -100,
            11,
            PollKind.LUNCH_ATTENDANCE_V1,
            context_date,
            datetime(2026, 7, 7, 10, tzinfo=UTC),
        )
    )
    polls.save(
        StoredPoll(
            "old-place",
            -100,
            12,
            PollKind.LUNCH_PLACE_ROSE_V1,
            context_date,
            datetime(2026, 7, 7, 9, tzinfo=UTC),
        )
    )
    polls.save(
        StoredPoll(
            "new-place",
            -100,
            13,
            PollKind.LUNCH_PLACE_SKYLINE_V1,
            context_date,
            datetime(2026, 7, 7, 10, tzinfo=UTC),
        )
    )
    polls.replace_selected_options(
        "old-attendance",
        42,
        {PollOption.LUNCH_EAT_IN_OFFICE},
        datetime(2026, 7, 7, 9, 1, tzinfo=UTC),
    )
    polls.replace_selected_options(
        "new-attendance",
        43,
        {PollOption.LUNCH_WOULD_ORDER},
        datetime(2026, 7, 7, 10, 1, tzinfo=UTC),
    )
    polls.replace_selected_options(
        "old-place",
        44,
        {PollOption.LUNCH_PLACE_ROSE_BEREZKA},
        datetime(2026, 7, 7, 9, 1, tzinfo=UTC),
    )
    polls.replace_selected_options(
        "new-place",
        45,
        {PollOption.LUNCH_PLACE_MCDONALDS},
        datetime(2026, 7, 7, 10, 1, tzinfo=UTC),
    )

    attendance = LunchAttendanceService(polls).list_office_users(-100, context_date)

    assert [user.display_name for user in attendance] == ["Анна", "Вера"]


@pytest.mark.parametrize(
    ("kind", "option", "included"),
    [
        (PollKind.LUNCH_ATTENDANCE_V1, PollOption.LUNCH_EAT_INDEPENDENTLY, True),
        (PollKind.LUNCH_ATTENDANCE_V1, PollOption.LUNCH_STAY_HOME, False),
        (
            PollKind.LUNCH_PLACE_SKYLINE_V1,
            PollOption.LUNCH_PLACE_MCDONALDS,
            True,
        ),
        (PollKind.LUNCH_PLACE_ROSE_V1, PollOption.LUNCH_PLACE_OTHER, True),
        (
            PollKind.LUNCH_PLACE_ROSE_V1,
            PollOption.LUNCH_PLACE_VIEW_RESULTS,
            False,
        ),
    ],
)
def test_lunch_attendance_includes_only_office_signals(
    database: Database,
    kind: PollKind,
    option: PollOption,
    included: bool,
) -> None:
    users = UserRepository(database)
    users.create_pending_user(
        TelegramProfile(42, "maxim", "Maxim", None),
        "Maxim",
    )
    users.approve_by_telegram_id(42)
    polls = PollRepository(database)
    context_date = date(2026, 7, 7)
    polls.save(
        StoredPoll(
            "poll-1",
            -100,
            10,
            kind,
            context_date,
            datetime(2026, 7, 7, 10, tzinfo=UTC),
        )
    )
    polls.replace_selected_options(
        "poll-1",
        42,
        {option},
        datetime(2026, 7, 7, 10, 1, tzinfo=UTC),
    )

    attendance = LunchAttendanceService(polls).list_office_users(-100, context_date)

    assert bool(attendance) is included


def test_lunch_attendance_combines_polls_without_duplicate_users(
    database: Database,
) -> None:
    users = UserRepository(database)
    for telegram_id, name in ((42, "Борис"), (43, "Анна")):
        users.create_pending_user(
            TelegramProfile(telegram_id, name.casefold(), name, None),
            name,
        )
        users.approve_by_telegram_id(telegram_id)
    polls = PollRepository(database)
    context_date = date(2026, 7, 7)
    for poll_id, kind in (
        ("attendance", PollKind.LUNCH_ATTENDANCE_V1),
        ("place", PollKind.LUNCH_PLACE_ROSE_V1),
    ):
        polls.save(
            StoredPoll(
                poll_id,
                -100,
                10,
                kind,
                context_date,
                datetime(2026, 7, 7, 10, tzinfo=UTC),
            )
        )
    polls.replace_selected_options(
        "attendance",
        42,
        {PollOption.LUNCH_EAT_INDEPENDENTLY},
        datetime(2026, 7, 7, 10, 1, tzinfo=UTC),
    )
    polls.replace_selected_options(
        "place",
        42,
        {PollOption.LUNCH_PLACE_ROSE_BEREZKA},
        datetime(2026, 7, 7, 10, 2, tzinfo=UTC),
    )
    polls.replace_selected_options(
        "place",
        43,
        {PollOption.LUNCH_PLACE_OTHER},
        datetime(2026, 7, 7, 10, 2, tzinfo=UTC),
    )

    attendance = LunchAttendanceService(polls).list_office_users(-100, context_date)

    assert [user.display_name for user in attendance] == ["Анна", "Борис"]


def test_replacing_poll_vote_returns_only_newly_selected_options(
    database: Database,
) -> None:
    polls = PollRepository(database)
    polls.save(
        StoredPoll(
            "poll-1",
            -100,
            10,
            PollKind.LUNCH_ATTENDANCE_V1,
            date(2026, 7, 7),
            datetime(2026, 7, 7, 10, tzinfo=UTC),
        )
    )
    first = polls.replace_selected_options(
        "poll-1",
        42,
        {PollOption.LUNCH_BRING_OWN},
        datetime(2026, 7, 7, 10, 1, tzinfo=UTC),
    )
    second = polls.replace_selected_options(
        "poll-1",
        42,
        {PollOption.LUNCH_BRING_OWN, PollOption.LUNCH_WOULD_ORDER},
        datetime(2026, 7, 7, 10, 2, tzinfo=UTC),
    )

    assert first == {PollOption.LUNCH_BRING_OWN}
    assert second == {PollOption.LUNCH_WOULD_ORDER}
