from __future__ import annotations

from datetime import UTC, date, datetime

from office_food_bot.database import Database
from office_food_bot.repositories import PollRepository
from office_food_bot.services.lunch_polls import (
    LUNCH_POLL_DEFINITION_CATALOG,
    ROSE_LUNCH_POLLS,
)
from office_food_bot.services.poll_tracking import PollTrackingService
from office_food_bot.services.polls import PollAction


def make_service(database: Database) -> PollTrackingService:
    return PollTrackingService(
        PollRepository(database),
        LUNCH_POLL_DEFINITION_CATALOG,
        clock=lambda: datetime(2026, 7, 7, 10, tzinfo=UTC),
    )


def test_poll_tracking_ignores_unknown_poll(database: Database) -> None:
    service = make_service(database)

    assert service.consume_action_requests("unknown-poll", 42, (1,)) == ()


def test_poll_tracking_ignores_option_without_action(database: Database) -> None:
    service = make_service(database)
    service.register_poll(
        "poll-1",
        123,
        10,
        ROSE_LUNCH_POLLS.place,
        date(2026, 7, 7),
    )

    assert service.consume_action_requests("poll-1", 42, (0, 1)) == ()


def test_poll_tracking_consumes_action_once(database: Database) -> None:
    service = make_service(database)
    service.register_poll(
        "poll-1",
        123,
        10,
        ROSE_LUNCH_POLLS.place,
        date(2026, 7, 7),
    )
    other_index = 3

    action_requests = service.consume_action_requests("poll-1", 42, (0, other_index))

    assert len(action_requests) == 1
    assert action_requests[0].poll_id == "poll-1"
    assert action_requests[0].chat_id == 123
    assert action_requests[0].action == PollAction.LUNCH_OTHER_FOOD_POLL
    assert service.consume_action_requests("poll-1", 42, (other_index,)) == ()
