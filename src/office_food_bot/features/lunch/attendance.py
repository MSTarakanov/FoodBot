from __future__ import annotations

from datetime import date

from office_food_bot.features.lunch.polls import ROSE_LUNCH_POLLS, SKYLINE_LUNCH_POLLS
from office_food_bot.features.polls.options import PollOption
from office_food_bot.models import PollKind, RegisteredUser
from office_food_bot.repositories import PollRepository

OFFICE_ATTENDANCE_OPTIONS = frozenset(
    {
        PollOption.LUNCH_BRING_OWN,
        PollOption.LUNCH_EAT_IN_OFFICE,
        PollOption.LUNCH_EAT_INDEPENDENTLY,
        PollOption.LUNCH_WOULD_ORDER,
    }
)
LUNCH_ATTENDANCE_KINDS = (PollKind.LUNCH_ATTENDANCE_V1,)
_LUNCH_PLACE_POLLS = (
    SKYLINE_LUNCH_POLLS.place,
    ROSE_LUNCH_POLLS.place,
)
LUNCH_PLACE_OPTIONS = frozenset(
    option
    for poll in _LUNCH_PLACE_POLLS
    for option in poll.options
    if option != PollOption.LUNCH_PLACE_VIEW_RESULTS
)
LUNCH_PLACE_KINDS = tuple(poll.kind for poll in _LUNCH_PLACE_POLLS)


class LunchAttendanceService:
    def __init__(self, polls: PollRepository) -> None:
        self._polls = polls

    def list_office_users(
        self,
        chat_id: int,
        context_date: date,
    ) -> tuple[RegisteredUser, ...]:
        users_by_id: dict[int, RegisteredUser] = {}
        for kinds, options in (
            (LUNCH_ATTENDANCE_KINDS, OFFICE_ATTENDANCE_OPTIONS),
            (LUNCH_PLACE_KINDS, LUNCH_PLACE_OPTIONS),
        ):
            poll = self._polls.latest_for_kinds(chat_id, context_date, kinds)
            if poll is None:
                continue
            for user in self._polls.list_active_users_with_any_option(
                poll.poll_id,
                options,
            ):
                users_by_id[user.id] = user
        return tuple(
            sorted(
                users_by_id.values(),
                key=lambda user: (user.display_name.casefold(), user.id),
            )
        )
