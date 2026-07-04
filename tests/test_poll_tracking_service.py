from __future__ import annotations

from office_food_bot.services.poll_tracking import PollAction, PollTrackingService


def test_poll_tracking_ignores_unknown_poll() -> None:
    service = PollTrackingService()

    assert service.consume_action_requests(
        "unknown-poll",
        (1,),
    ) == ()


def test_poll_tracking_ignores_option_without_action() -> None:
    service = PollTrackingService()
    service.track_poll(
        "poll-1",
        123,
        {2: PollAction.LUNCH_OTHER_FOOD_POLL},
    )

    assert service.consume_action_requests("poll-1", (0, 1)) == ()


def test_poll_tracking_consumes_action_once() -> None:
    service = PollTrackingService()
    service.track_poll(
        "poll-1",
        123,
        {2: PollAction.LUNCH_OTHER_FOOD_POLL},
    )

    action_requests = service.consume_action_requests("poll-1", (0, 2))

    assert len(action_requests) == 1
    assert action_requests[0].poll_id == "poll-1"
    assert action_requests[0].chat_id == 123
    assert action_requests[0].action == PollAction.LUNCH_OTHER_FOOD_POLL
    assert service.consume_action_requests("poll-1", (2,)) == ()
