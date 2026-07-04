from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum


class PollAction(StrEnum):
    LUNCH_OTHER_FOOD_POLL = "lunch_other_food_poll"


@dataclass(frozen=True, slots=True)
class PollActionRequest:
    poll_id: str
    chat_id: int
    action: PollAction


@dataclass(slots=True)
class TrackedPoll:
    chat_id: int
    option_actions: dict[int, PollAction]
    consumed_actions: set[PollAction] = field(default_factory=set)


class PollTrackingService:
    def __init__(self) -> None:
        self._tracked_polls: dict[str, TrackedPoll] = {}

    def track_poll(
        self,
        poll_id: str,
        chat_id: int,
        option_actions: Mapping[int, PollAction],
    ) -> None:
        self._tracked_polls[poll_id] = TrackedPoll(
            chat_id=chat_id,
            option_actions=dict(option_actions),
        )

    def consume_action_requests(
        self,
        poll_id: str,
        selected_option_ids: tuple[int, ...],
    ) -> tuple[PollActionRequest, ...]:
        tracked_poll = self._tracked_polls.get(poll_id)
        if tracked_poll is None:
            return ()

        action_requests: list[PollActionRequest] = []
        for option_id in selected_option_ids:
            action = tracked_poll.option_actions.get(option_id)
            if action is None or action in tracked_poll.consumed_actions:
                continue

            tracked_poll.consumed_actions.add(action)
            action_requests.append(
                PollActionRequest(
                    poll_id=poll_id,
                    chat_id=tracked_poll.chat_id,
                    action=action,
                )
            )

        return tuple(action_requests)
